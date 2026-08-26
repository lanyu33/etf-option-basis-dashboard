# -*- coding: utf-8 -*-
"""用通达信 2026-08-26 盘中快照(≈09:57)更新 dashboard 三处数据:
1. option_basis_data.json (主数据 rows + etfs spot/月份)
2. HTML FALLBACK (前端兜底)
3. option_server.py FALLBACK_DATA (服务端兜底)

说明:
- 8/26 为 8月合约到期日, 本次只保留 9月/12月/2027年3月(无 10月合约)
- 行情为盘中≈09:57 快照(非收盘), TDX 源冻结于该时刻
- 部分 ATM 合约盘中无成交(NOW=0), 以 PrevClose 替代参与合成期货计算
"""
import datetime, json, re, io

today = datetime.date(2026, 8, 26)
expiries = {'9月': '2026-09-23', '12月': '2026-12-23', '2027年3月': '2027-03-24'}

# (etf, code, spot, prev_close, month, K, call_code, call, put_code, put)
# spot = ETF 最新价(NOW); prev_close = ETF 昨收(Close 反推); call/put = 合约最新价(NOW=0 用 PrevClose)
data = [
    ('50ETF','510050.SH',3.000,2.982,'9月',3.000,'10010974.SH',0.0445,'10010983.SH',0.0520),
    ('50ETF','510050.SH',3.000,2.982,'12月',3.000,'10011429.SH',0.0906,'10011438.SH',0.1303),
    ('50ETF','510050.SH',3.000,2.982,'2027年3月',3.000,'10012166.SH',0.1169,'10012175.SH',0.1689),
    ('300ETF','510300.SH',4.632,4.616,'9月',4.600,'10010992.SH',0.1014,'10011001.SH',0.0871),
    ('300ETF','510300.SH',4.632,4.616,'12月',4.600,'10011445.SH',0.1682,'10011454.SH',0.2160),
    ('300ETF','510300.SH',4.632,4.616,'2027年3月',4.600,'10012183.SH',0.1920,'10012192.SH',0.2988),
    ('500ETF','510500.SH',7.743,7.726,'9月',7.750,'10012073.SH',0.2010,'10012082.SH',0.2846),
    ('500ETF','510500.SH',7.743,7.726,'12月',7.750,'10012091.SH',0.3350,'10012100.SH',0.5816),
    ('500ETF','510500.SH',7.743,7.726,'2027年3月',7.750,'10012203.SH',0.3765,'10012212.SH',0.8008),  # 沽 NOW=0 -> PrevClose 0.8008
    ('科创50ETF','588000.SH',1.698,1.693,'9月',1.700,'10011030.SH',0.0718,'10011039.SH',0.0816),
    ('科创50ETF','588000.SH',1.698,1.693,'12月',1.700,'10011486.SH',0.1322,'10011495.SH',0.1697),
    ('科创50ETF','588000.SH',1.698,1.693,'2027年3月',1.700,'10012253.SH',0.1697,'10012254.SH',0.2258),  # 购 NOW=0 -> PrevClose 0.1697
]

SOURCE = '通达信 2026-08-26 盘中09:57'
UPDATED = '2026-08-26 09:57'


def is_standard_strike(strike):
    return abs(strike - round(strike * 20) / 20) < 1e-6


def contract_unit(underlying, strike):
    if underlying == '510500' and not is_standard_strike(strike):
        return 10180
    return 10000


def put_margin(prev_close, strike, put_price, unit):
    otm = max(prev_close - strike, 0.0)
    base = put_price + max(0.12 * prev_close - otm, 0.07 * strike)
    return round(min(base, strike) * unit, 2)


rows = []
for etf, code, spot, pc, month, K, cc, c, ppc, p in data:
    exp = datetime.date.fromisoformat(expiries[month])
    days = max((exp - today).days, 1)
    F = round(c - p + K, 4)
    basis = round(F - spot, 4)
    basis_pct = round(basis / spot * 100, 4)
    annual_pct = round(basis_pct * 365 / days, 2)
    und = code.replace('.SH', '')
    unit = contract_unit(und, K)
    call_premium = round(c * unit, 2)
    pm = put_margin(pc, K, p, unit)
    r = {
        'etf': etf, 'etf_code': code, 'spot': spot, 'month': month,
        'expiry': expiries[month], 'days': days, 'strike': K,
        'call_code': cc, 'call': c, 'put_code': ppc, 'put': p,
        'synthetic': F, 'basis': basis, 'basis_pct': basis_pct, 'annual_pct': annual_pct,
        'unit': unit, 'call_premium': call_premium, 'put_margin': pm, 'margin_total': round(call_premium + pm, 2),
    }
    rows.append(r)

print('--- 12 行 ATM 合成期货贴水 (TDX 08-26 盘中09:57) ---')
for r in rows:
    print('{:<10} {:<10} spot={:<6} K={:<6} C={:<7} P={:<7} F={:<8} basis={:<8} annual={}% 占用={}'.format(
        r['etf'], r['month'], r['spot'], r['strike'], r['call'], r['put'], r['synthetic'], r['basis'], r['annual_pct'], r['margin_total']))

# ---------- 1. option_basis_data.json ----------
with io.open('option_basis_data.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

d['source'] = SOURCE
d['updated_at'] = UPDATED
d['rows'] = rows

spot_map = {'510050.SH': 3.000, '510300.SH': 4.632, '510500.SH': 7.743, '588000.SH': 1.698}
for e in d.get('etfs', []):
    if e.get('code') in spot_map:
        e['spot'] = spot_map[e['code']]
    # 去除已到期的 8月合约月份
    e['months'] = [m for m in e.get('months', []) if m.get('month') != '8月']

with io.open('option_basis_data.json', 'w', encoding='utf-8') as f:
    json.dump(d, f, ensure_ascii=False, indent=1)
print('json updated:', len(rows), 'rows (8月已剔除)')

# ---------- 2 & 3. HTML FALLBACK + option_server FALLBACK_DATA ----------
rows_js = []
for r in rows:
    rows_js.append(
        '{etf:"%s",etf_code:"%s",spot:%.3f,month:"%s",expiry:"%s",days:%d,strike:%.3f,'
        'call_code:"%s",call:%.4f,put_code:"%s",put:%.4f,synthetic:%.4f,basis:%.4f,basis_pct:%.4f,annual_pct:%.2f}' % (
            r['etf'], r['etf_code'], r['spot'], r['month'], r['expiry'], r['days'], r['strike'],
            r['call_code'], r['call'], r['put_code'], r['put'], r['synthetic'], r['basis'], r['basis_pct'], r['annual_pct']))

rows_py = []
for r in rows:
    rows_py.append(
        '{"etf":"%s","etf_code":"%s","spot":%.3f,"month":"%s","expiry":"%s","days":%d,"strike":%.3f,'
        '"call_code":"%s","call":%.4f,"put_code":"%s","put":%.4f,"synthetic":%.4f,"basis":%.4f,"basis_pct":%.4f,"annual_pct":%.2f}' % (
            r['etf'], r['etf_code'], r['spot'], r['month'], r['expiry'], r['days'], r['strike'],
            r['call_code'], r['call'], r['put_code'], r['put'], r['synthetic'], r['basis'], r['basis_pct'], r['annual_pct']))

html_path = 'etf_option_basis_dashboard.html'
with io.open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()
html_new_rows = '  rows: [\n' + '\n'.join('    ' + r + ',' for r in rows_js) + '\n  ]\n};'
html = re.sub(r'var FALLBACK = \{\n  source:.*?\n  updated_at:.*?\n  rows:.*?\n\};',
              'var FALLBACK = {\n  source: "%s(兜底)",\n  updated_at: "%s",\n%s' % (SOURCE, UPDATED, html_new_rows),
              html, count=1, flags=re.S)
with io.open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)
print('HTML FALLBACK updated')

py_path = 'option_server.py'
with io.open(py_path, 'r', encoding='utf-8') as f:
    py = f.read()
py_new_rows = '    "rows": [\n' + '\n'.join('        ' + r + ',' for r in rows_py) + '\n    ],\n}'
py = re.sub(r'FALLBACK_DATA = \{\n    "source":.*?\n    "updated_at":.*?\n    "rows":.*?\n\}',
            'FALLBACK_DATA = {\n    "source": "%s(兜底)",\n    "updated_at": "%s",\n%s' % (SOURCE, UPDATED, py_new_rows),
            py, count=1, flags=re.S)
with io.open(py_path, 'w', encoding='utf-8') as f:
    f.write(py)
print('option_server.py FALLBACK_DATA updated')
