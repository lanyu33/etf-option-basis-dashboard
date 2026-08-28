# -*- coding: utf-8 -*-
"""
ETF 期权合成期货贴水 Dashboard - 本地数据服务
数据源: 新浪财经批量接口 (与 Wind 2026-08-12 收盘数据交叉验证一致)
运行: python option_server.py [port]  (默认 8899)
接口:
  GET  /             -> dashboard HTML
  GET  /api/data     -> 当前数据 JSON
  POST /api/refresh  -> 重新拉取实时数据并返回
"""
import json
import os
import re
import calendar
import datetime
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

import requests

# ---------------- 配置 ----------------
PORT = 8899
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_FILE = os.path.join(BASE_DIR, "etf_option_basis_dashboard.html")
DATA_FILE = os.path.join(BASE_DIR, "option_basis_data.json")

HEADERS = {
    "Referer": "https://stock.finance.sina.com.cn/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/97.0 Safari/537.36",
}

ETFS = [
    {"name": "50ETF",     "code": "510050.SH", "underlying": "510050", "sh": "sh510050"},
    {"name": "300ETF",    "code": "510300.SH", "underlying": "510300", "sh": "sh510300"},
    {"name": "500ETF",    "code": "510500.SH", "underlying": "510500", "sh": "sh510500"},
    {"name": "科创50ETF", "code": "588000.SH", "underlying": "588000", "sh": "sh588000"},
]

# 无风险利率(年化, 用于参考展示)
RISK_FREE = 0.018

# 初始数据(2026-08-12 Wind 收盘, 服务器启动时作为兜底)
FALLBACK_DATA = {
    "source": "通达信 2026-08-26 盘中09:57(兜底)",
    "updated_at": "2026-08-26 09:57",
    "rows": [
        {"etf":"50ETF","etf_code":"510050.SH","spot":3.000,"month":"9月","expiry":"2026-09-23","days":28,"strike":3.000,"call_code":"10010974.SH","call":0.0445,"put_code":"10010983.SH","put":0.0520,"synthetic":2.9925,"basis":-0.0075,"basis_pct":-0.2500,"annual_pct":-3.26},
        {"etf":"50ETF","etf_code":"510050.SH","spot":3.000,"month":"12月","expiry":"2026-12-23","days":119,"strike":3.000,"call_code":"10011429.SH","call":0.0906,"put_code":"10011438.SH","put":0.1303,"synthetic":2.9603,"basis":-0.0397,"basis_pct":-1.3233,"annual_pct":-4.06},
        {"etf":"50ETF","etf_code":"510050.SH","spot":3.000,"month":"2027年3月","expiry":"2027-03-24","days":210,"strike":3.000,"call_code":"10012166.SH","call":0.1169,"put_code":"10012175.SH","put":0.1689,"synthetic":2.9480,"basis":-0.0520,"basis_pct":-1.7333,"annual_pct":-3.01},
        {"etf":"300ETF","etf_code":"510300.SH","spot":4.632,"month":"9月","expiry":"2026-09-23","days":28,"strike":4.600,"call_code":"10010992.SH","call":0.1014,"put_code":"10011001.SH","put":0.0871,"synthetic":4.6143,"basis":-0.0177,"basis_pct":-0.3821,"annual_pct":-4.98},
        {"etf":"300ETF","etf_code":"510300.SH","spot":4.632,"month":"12月","expiry":"2026-12-23","days":119,"strike":4.600,"call_code":"10011445.SH","call":0.1682,"put_code":"10011454.SH","put":0.2160,"synthetic":4.5522,"basis":-0.0798,"basis_pct":-1.7228,"annual_pct":-5.28},
        {"etf":"300ETF","etf_code":"510300.SH","spot":4.632,"month":"2027年3月","expiry":"2027-03-24","days":210,"strike":4.600,"call_code":"10012183.SH","call":0.1920,"put_code":"10012192.SH","put":0.2988,"synthetic":4.4932,"basis":-0.1388,"basis_pct":-2.9965,"annual_pct":-5.21},
        {"etf":"500ETF","etf_code":"510500.SH","spot":7.743,"month":"9月","expiry":"2026-09-23","days":28,"strike":7.750,"call_code":"10012073.SH","call":0.2010,"put_code":"10012082.SH","put":0.2846,"synthetic":7.6664,"basis":-0.0766,"basis_pct":-0.9893,"annual_pct":-12.90},
        {"etf":"500ETF","etf_code":"510500.SH","spot":7.743,"month":"12月","expiry":"2026-12-23","days":119,"strike":7.750,"call_code":"10012091.SH","call":0.3350,"put_code":"10012100.SH","put":0.5816,"synthetic":7.5034,"basis":-0.2396,"basis_pct":-3.0944,"annual_pct":-9.49},
        {"etf":"500ETF","etf_code":"510500.SH","spot":7.743,"month":"2027年3月","expiry":"2027-03-24","days":210,"strike":7.750,"call_code":"10012203.SH","call":0.3765,"put_code":"10012212.SH","put":0.8008,"synthetic":7.3257,"basis":-0.4173,"basis_pct":-5.3894,"annual_pct":-9.37},
        {"etf":"科创50ETF","etf_code":"588000.SH","spot":1.698,"month":"9月","expiry":"2026-09-23","days":28,"strike":1.700,"call_code":"10011030.SH","call":0.0718,"put_code":"10011039.SH","put":0.0816,"synthetic":1.6902,"basis":-0.0078,"basis_pct":-0.4594,"annual_pct":-5.99},
        {"etf":"科创50ETF","etf_code":"588000.SH","spot":1.698,"month":"12月","expiry":"2026-12-23","days":119,"strike":1.700,"call_code":"10011486.SH","call":0.1322,"put_code":"10011495.SH","put":0.1697,"synthetic":1.6625,"basis":-0.0355,"basis_pct":-2.0907,"annual_pct":-6.41},
        {"etf":"科创50ETF","etf_code":"588000.SH","spot":1.698,"month":"2027年3月","expiry":"2027-03-24","days":210,"strike":1.700,"call_code":"10012253.SH","call":0.1697,"put_code":"10012254.SH","put":0.2258,"synthetic":1.6439,"basis":-0.0541,"basis_pct":-3.1861,"annual_pct":-5.54},
    ],
}

# ---------------- 数据抓取 ----------------

def get_spots():
    """批量获取 4 个 ETF 现货价 (新浪 hq, 毫秒级)"""
    url = "https://hq.sinajs.cn/list=" + ",".join(e["sh"] for e in ETFS)
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.encoding = "gbk"
    spots = {}
    for line in r.text.strip().split("\n"):
        code = line[line.find("hq_str_") + 7:line.find("=")]
        data = line[line.find('"') + 1:line.rfind('"')].split(",")
        if len(data) > 3:
            try:
                spots[code[2:]] = {"price": float(data[3]), "prev_close": float(data[2])}
            except (ValueError, IndexError):
                pass
    return spots


def get_months(symbol_name):
    """获取合约月份列表 ['202608','202609','202612','202703']"""
    url = "https://stock.finance.sina.com.cn/futures/api/openapi.php/StockOptionService.getStockName"
    r = requests.get(url, params={"exchange": "null", "cate": symbol_name}, timeout=20)
    j = r.json()
    months = j["result"]["data"]["contractMonth"]
    seen = []
    for m in months:
        mm = m.replace("-", "")
        if mm not in seen:
            seen.append(mm)
    return seen[:4]


def get_contract_codes(underlying, yymm, direction):
    """direction: 'UP'=认购 'DOWN'=认沽; 返回代码列表(按行权价升序)"""
    url = "https://hq.sinajs.cn/list=OP_{0}_{1}{2}".format(direction, underlying, yymm)
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.encoding = "gbk"
    text = r.text.strip()
    codes = []
    start = text.find('"') + 1
    end = text.rfind('"')
    if 0 < start < end:
        for token in text[start:end].split(","):
            token = token.strip()
            if token.startswith("CON_OP_"):
                codes.append(token[7:])
    return codes


def get_quotes(codes):
    """批量获取合约行情 {code: {price, strike, prev_close}}"""
    if not codes:
        return {}
    url = "https://hq.sinajs.cn/list=" + ",".join("CON_OP_" + c for c in codes)
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.encoding = "gbk"
    quotes = {}
    for line in r.text.strip().split("\n"):
        code = line[line.find("hq_str_") + 7:line.find("=")].replace("CON_OP_", "")
        data = line[line.find('"') + 1:line.rfind('"')].split(",")
        if len(data) > 8:
            try:
                quotes[code] = {
                    "price": float(data[2]),
                    "strike": float(data[7]),
                    "prev_close": float(data[8]),
                }
            except (ValueError, IndexError):
                pass
    return quotes


def expiry_from_month(yymm):
    """给定 '202608', 返回第4个星期三的到期日 datetime"""
    year = int(yymm[:4])
    month = int(yymm[4:6])
    cal = calendar.monthcalendar(year, month)
    wed_days = [w[2] for w in cal if w[2] != 0]
    day = wed_days[3] if len(wed_days) > 3 else wed_days[-1]
    return datetime.date(year, month, day)


def month_label(yymm):
    """'202608' -> '8月'; '202703' -> '2027年3月'"""
    year = int(yymm[:4])
    month = int(yymm[4:6])
    this_year = datetime.date.today().year
    if year == this_year:
        return "{}月".format(month)
    return "{}年{}月".format(year, month)


def is_standard_strike(strike):
    """标准行权价 = 0.05 的整数倍(排除带A除权调整档, 如 8.104/7.613)"""
    return abs(strike - round(strike * 20) / 20) < 1e-6


def contract_unit(underlying, strike):
    """合约单位: 标准10000, 500ETF除权调整档(带A)为10180"""
    if underlying == "510500" and not is_standard_strike(strike):
        return 10180
    return 10000


def put_margin(prev_close, strike, put_price, unit):
    """认沽期权义务仓保证金(每张, 上交所ETF期权公式)
    保证金 = min[权利金 + max(12%*前收盘 - 虚值额, 7%*行权价), 行权价] * 合约单位
    虚值额(认沽) = max(前收盘 - 行权价, 0)
    """
    otm = max(prev_close - strike, 0.0)
    base = put_price + max(0.12 * prev_close - otm, 0.07 * strike)
    return round(min(base, strike) * unit, 2)


def refresh_data():
    """拉取实时数据, 计算贴水, 返回结果 dict
    结构: {source, updated_at, rows(平值, 供KPI/图表), etfs(全合约, 供tab表)}
    """
    today = datetime.date.today()
    spots = get_spots()
    rows = []
    etfs = []

    for etf in ETFS:
        underlying = etf["underlying"]
        spot_info = spots.get(underlying)
        if not spot_info:
            continue
        spot = spot_info["price"]
        prev_close = spot_info.get("prev_close", spot)
        months = get_months(etf["name"])
        etf_entry = {
            "name": etf["name"],
            "code": etf["code"],
            "spot": round(spot, 4),
            "months": [],
        }

        for yymm in months:
            # 获取该月认购/认沽代码 (OP_UP 接口用 yymm 后4位)
            yymm4 = yymm[-4:]
            call_codes = get_contract_codes(underlying, yymm4, "UP")
            put_codes = get_contract_codes(underlying, yymm4, "DOWN")
            if not call_codes or not put_codes:
                continue  # 该月无合约(如500ETF 202703)

            # 批量拿行情
            quotes = get_quotes(call_codes + put_codes)
            if not quotes:
                continue

            # 按行权价配对 Call/Put
            calls = {}
            for c in call_codes:
                q = quotes.get(c)
                if q and q["strike"] > 0:
                    calls[q["strike"]] = (c, q["price"])
            puts = {}
            for c in put_codes:
                q = quotes.get(c)
                if q and q["strike"] > 0:
                    puts[q["strike"]] = (c, q["price"])

            strikes = sorted(set(calls.keys()) & set(puts.keys()))
            if not strikes:
                continue

            expiry = expiry_from_month(yymm)
            days = max((expiry - today).days, 1)
            label = month_label(yymm)

            # 平值行权价: 优先从标准合约(不含A)里选
            std_strikes = [s for s in strikes if is_standard_strike(s)]
            pool = std_strikes if std_strikes else strikes
            atm_strike = min(pool, key=lambda s: abs(s - spot))

            strikes_list = []
            for s in strikes:
                cc, cp = calls[s]
                pc, pp = puts[s]
                synthetic = round(cp - pp + s, 4)
                basis = round(synthetic - spot, 4)
                basis_pct = round(basis / spot * 100, 4)
                annual_pct = round(basis_pct * 365 / days, 2)
                unit = contract_unit(underlying, s)
                call_premium = round(cp * unit, 2)          # 买购权利金(全额)
                pm = put_margin(prev_close, s, pp, unit)    # 卖沽保证金
                margin_total = round(call_premium + pm, 2)  # 合计占用
                strikes_list.append({
                    "strike": s,
                    "call_code": cc + ".SH",
                    "call": cp,
                    "put_code": pc + ".SH",
                    "put": pp,
                    "synthetic": synthetic,
                    "basis": basis,
                    "basis_pct": basis_pct,
                    "annual_pct": annual_pct,
                    "atm": (s == atm_strike),
                    "unit": unit,
                    "call_premium": call_premium,
                    "put_margin": pm,
                    "margin_total": margin_total,
                })

                # 平值行同步进 rows (KPI/图表用)
                if s == atm_strike:
                    rows.append({
                        "etf": etf["name"],
                        "etf_code": etf["code"],
                        "spot": round(spot, 4),
                        "month": label,
                        "expiry": expiry.strftime("%Y-%m-%d"),
                        "days": days,
                        "strike": s,
                        "call_code": cc + ".SH",
                        "call": cp,
                        "put_code": pc + ".SH",
                        "put": pp,
                        "synthetic": synthetic,
                        "basis": basis,
                        "basis_pct": basis_pct,
                        "annual_pct": annual_pct,
                        "unit": unit,
                        "call_premium": call_premium,
                        "put_margin": pm,
                        "margin_total": margin_total,
                    })

            etf_entry["months"].append({
                "month": label,
                "expiry": expiry.strftime("%Y-%m-%d"),
                "days": days,
                "strikes": strikes_list,
            })

        if etf_entry["months"]:
            etfs.append(etf_entry)

    now = datetime.datetime.now()
    return {
        "source": "新浪财经实时接口 (akshare)",
        "updated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "rows": rows,
        "etfs": etfs,
    }


# ---------------- 状态 ----------------
_state = {
    "data": None,          # 当前数据
    "refreshing": False,   # 是否正在刷新
    "lock": threading.Lock(),
}


def load_initial():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
            if "etfs" not in d:
                # 旧格式: 从平值 rows 生成简化 etfs
                d["etfs"] = etfs_from_rows(d.get("rows", []))
            _state["data"] = d
            return
        except Exception:
            pass
    fb = dict(FALLBACK_DATA)
    fb["etfs"] = etfs_from_rows(fb["rows"])
    _state["data"] = fb


def etfs_from_rows(rows):
    """从平值 rows 生成简化 etfs 结构 (每月仅平值1行, 兜底用)"""
    etfs = []
    seen = {}
    for r in rows:
        key = r["etf"]
        if key not in seen:
            seen[key] = {"name": key, "code": r["etf_code"], "spot": r["spot"], "months": []}
            etfs.append(seen[key])
        seen[key]["months"].append({
            "month": r["month"],
            "expiry": r["expiry"],
            "days": r["days"],
            "strikes": [{
                "strike": r["strike"],
                "call_code": r["call_code"],
                "call": r["call"],
                "put_code": r["put_code"],
                "put": r["put"],
                "synthetic": r["synthetic"],
                "basis": r["basis"],
                "basis_pct": r["basis_pct"],
                "annual_pct": r["annual_pct"],
                "atm": True,
            }],
        })
    return etfs


def do_refresh():
    """执行刷新 (线程安全), 返回 (ok, message)"""
    with _state["lock"]:
        if _state["refreshing"]:
            return False, "正在刷新中, 请稍候"
        _state["refreshing"] = True
    try:
        data = refresh_data()
        with _state["lock"]:
            _state["data"] = data
            try:
                with open(DATA_FILE, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
        return True, "刷新成功"
    except Exception as e:
        return False, "刷新失败: {}".format(str(e))
    finally:
        with _state["lock"]:
            _state["refreshing"] = False


# ---------------- HTTP 服务器 ----------------
class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html):
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            try:
                with open(HTML_FILE, "r", encoding="utf-8") as f:
                    self._send_html(f.read())
            except Exception as e:
                self._send_json({"error": str(e)}, 500)
        elif path == "/api/data":
            with _state["lock"]:
                data = _state["data"] or FALLBACK_DATA
            self._send_json(data)
        elif path == "/api/status":
            with _state["lock"]:
                self._send_json({"refreshing": _state["refreshing"], "data": _state["data"] is not None})
        else:
            self._send_json({"error": "not found"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/refresh":
            ok, msg = do_refresh()
            with _state["lock"]:
                data = _state["data"]
            if ok:
                self._send_json({"ok": True, "message": msg, "data": data})
            else:
                self._send_json({"ok": False, "message": msg, "data": data}, 200)
        else:
            self._send_json({"error": "not found"}, 404)


def main():
    load_initial()
    port = PORT
    try:
        server = HTTPServer(("127.0.0.1", port), Handler)
    except OSError:
        port = PORT + 1
        server = HTTPServer(("127.0.0.1", port), Handler)
    print("Dashboard server running at http://127.0.0.1:{}/".format(port))
    server.serve_forever()


if __name__ == "__main__":
    main()
