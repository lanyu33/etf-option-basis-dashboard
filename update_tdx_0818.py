# -*- coding: utf-8 -*-
"""用通达信 8/18 收盘数据更新 dashboard 三处数据:
1. option_basis_data.json (主数据 rows + etfs spot)
2. HTML FALLBACK (前端兜底)
3. option_server.py FALLBACK_DATA (服务端兜底)
"""
import datetime, json, re, io

today = datetime.date(2026, 8, 19)
expiries = {'8月': '2026-08-26', '9月': '2026-09-23', '12月': '2026-12-23', '2027年3月': '2027-03-24'}

# (etf, code, spot, month, K, call_code, call, put_code, put) — 通达信 8/18 收盘
data = [
    ('50ETF','510050.SH',3.047,'8月',3.000,'10011855.SH',0.0548,'10011864.SH',0.0113),
    ('50ETF','510050.SH',3.047,'9月',3.000,'10010974.SH',0.0713,'10010983.SH',0.0437),
    ('50ETF','510050.SH',3.047,'12月',3.000,'10011429.SH',0.1128,'10011438.SH',0.1106),
    ('50ETF','510050.SH',3.047,'2027年3月',3.000,'10012166.SH',0.1388,'10012175.SH',0.1532),
    ('300ETF','510300.SH',4.787,'8月',4.800,'10011871.SH',0.0318,'10011880.SH',0.0613),
    ('300ETF','510300.SH',4.787,'9月',4.800,'10010994.SH',0.0736,'10011003.SH',0.1270),
    ('300ETF','510300.SH',4.787,'12月',4.800,'10011447.SH',0.1420,'10011456.SH',0.2503),
    ('300ETF','510300.SH',4.787,'2027年3月',4.800,'10012185.SH',0.1742,'10012194.SH',0.3385),
    ('500ETF','510500.SH',8.185,'8月',8.250,'10012057.SH',0.0642,'10012066.SH',0.1870),
    ('500ETF','510500.SH',8.185,'9月',8.250,'10012075.SH',0.1636,'10012084.SH',0.3630),
    ('500ETF','510500.SH',8.185,'12月',8.250,'10012093.SH',0.2852,'10012102.SH',0.6547),
    ('500ETF','510500.SH',8.185,'2027年3月',8.250,'10012205.SH',0.3420,'10012214.SH',0.8575),
    ('科创50ETF','588000.SH',1.888,'8月',1.900,'10011905.SH',0.0361,'10011914.SH',0.0525),
    ('科创50ETF','588000.SH',1.888,'9月',1.900,'10011561.SH',0.0765,'10011563.SH',0.1030),
    ('科创50ETF','588000.SH',1.888,'12月',1.900,'10011565.SH',0.1356,'10011567.SH',0.1943),
    ('科创50ETF','588000.SH',1.888,'2027年3月',1.900,'10012220.SH',0.1696,'10012229.SH',0.2453),
]

rows = []
for etf, code, spot, month, K, cc, c, pc, p in data:
    exp = datetime.date.fromisoformat(expiries[month])
    days = max((exp - today).days, 1)
    F = round(c - p + K, 4)
    basis = round(F - spot, 4)
    basis_pct = round(basis / spot * 100, 4)
    annual_pct = round(basis_pct * 365 / days, 2)
    rows.append({
        'etf': etf, 'etf_code': code, 'spot': spot, 'month': month,
        'expiry': expiries[month], 'days': days, 'strike': K,
        'call_code': cc, 'call': c, 'put_code': pc, 'put': p,
        'synthetic': F, 'basis': basis, 'basis_pct': basis_pct, 'annual_pct': annual_pct,
    })

for r in rows:
    print('{:<10} {:<10} spot={:<6} K={:<6} C={:<6} P={:<6} F={:<8} basis={:<8} annual={}%'.format(
        r['etf'], r['month'], r['spot'], r['strike'], r['call'], r['put'], r['synthetic'], r['basis'], r['annual_pct']))

# ---------- 1. option_basis_data.json ----------
with io.open('option_basis_data.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

d['source'] = '通达信 2026-08-18 收盘'
d['updated_at'] = '2026-08-18 15:30'
# 更新平值 rows（保留保证金字段: 用 option_server 的公式重算）
import sys
sys.path.insert(0, '.')
import option_server as s
new_rows = []
for r in rows:
    und = r['etf_code'].replace('.SH', '')
    unit = s.contract_unit(und, r['strike'])
    r['unit'] = unit
    r['call_premium'] = round(r['call'] * unit, 2)
    # 保证金需要前收盘价 — 用通达信 Close 字段
    prev_close_map = {'510050': 3.052, '510300': 4.801, '510500': 8.197, '588000': 1.888}
    pc_price = prev_close_map.get(und, r['spot'])
    r['put_margin'] = s.put_margin(pc_price, r['strike'], r['put'], unit)
    r['margin_total'] = round(r['call_premium'] + r['put_margin'], 2)
    new_rows.append(r)
d['rows'] = new_rows

# 更新 etfs 的 spot
spot_map = {'510050.SH': 3.047, '510300.SH': 4.787, '510500.SH': 8.185, '588000.SH': 1.888}
for e in d.get('etfs', []):
    if e.get('code') in spot_map:
        e['spot'] = spot_map[e['code']]

with io.open('option_basis_data.json', 'w', encoding='utf-8') as f:
    json.dump(d, f, ensure_ascii=False, indent=1)
print('json updated:', len(new_rows), 'rows')

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
              'var FALLBACK = {\n  source: "通达信 2026-08-18 收盘(兜底)",\n  updated_at: "2026-08-18 15:30",\n' + html_new_rows,
              html, count=1, flags=re.S)
with io.open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)
print('HTML FALLBACK updated')

py_path = 'option_server.py'
with io.open(py_path, 'r', encoding='utf-8') as f:
    py = f.read()
py_new_rows = '    "rows": [\n' + '\n'.join('        ' + r + ',' for r in rows_py) + '\n    ],\n}'
py = re.sub(r'FALLBACK_DATA = \{\n    "source":.*?\n    "updated_at":.*?\n    "rows":.*?\n\}',
            'FALLBACK_DATA = {\n    "source": "通达信 2026-08-18 收盘(兜底)",\n    "updated_at": "2026-08-18 15:30",\n' + py_new_rows,
            py, count=1, flags=re.S)
with io.open(py_path, 'w', encoding='utf-8') as f:
    f.write(py)
print('option_server.py FALLBACK_DATA updated')
