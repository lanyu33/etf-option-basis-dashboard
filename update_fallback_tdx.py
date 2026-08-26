# -*- coding: utf-8 -*-
"""用通达信 8/14 收盘数据更新 dashboard 兜底数据 (HTML FALLBACK + option_server FALLBACK_DATA)"""
import datetime, re, io

today = datetime.date(2026, 8, 15)
expiries = {'8月': '2026-08-26', '9月': '2026-09-23', '12月': '2026-12-23', '2027年3月': '2027-03-24'}

# (etf, code, spot, month, K, call_code, call, put_code, put) — 通达信 MCP 8/14 收盘
data = [
    ('50ETF','510050.SH',3.021,'8月',3.000,'10011855.SH',0.0418,'10011864.SH',0.0212),
    ('50ETF','510050.SH',3.021,'9月',3.000,'10010974.SH',0.0634,'10010983.SH',0.0552),
    ('50ETF','510050.SH',3.021,'12月',3.000,'10011429.SH',0.1070,'10011438.SH',0.1229),
    ('50ETF','510050.SH',3.021,'2027年3月',3.000,'10012166.SH',0.1362,'10012175.SH',0.1639),
    ('300ETF','510300.SH',4.726,'8月',4.700,'10011870.SH',0.0616,'10011879.SH',0.0447),
    ('300ETF','510300.SH',4.726,'9月',4.700,'10010993.SH',0.1024,'10011002.SH',0.1045),
    ('300ETF','510300.SH',4.726,'12月',4.700,'10011446.SH',0.1692,'10011455.SH',0.2273),
    ('300ETF','510300.SH',4.726,'2027年3月',4.700,'10012184.SH',0.2002,'10012193.SH',0.3142),
    ('500ETF','510500.SH',7.998,'8月',8.000,'10012056.SH',0.1130,'10012065.SH',0.1533),
    ('500ETF','510500.SH',7.998,'9月',8.000,'10012074.SH',0.2081,'10012083.SH',0.3089),
    ('500ETF','510500.SH',7.998,'12月',8.000,'10012092.SH',0.3394,'10012101.SH',0.5832),
    ('500ETF','510500.SH',7.998,'2027年3月',8.000,'10012204.SH',0.4018,'10012213.SH',0.7962),
    ('科创50ETF','588000.SH',1.814,'8月',1.800,'10012122.SH',0.0571,'10012124.SH',0.0478),
    ('科创50ETF','588000.SH',1.814,'9月',1.800,'10011032.SH',0.0915,'10011041.SH',0.0930),
    ('科创50ETF','588000.SH',1.814,'12月',1.800,'10011523.SH',0.1524,'10011524.SH',0.1831),
    ('科创50ETF','588000.SH',1.814,'2027年3月',1.800,'10012218.SH',0.1907,'10012227.SH',0.2392),
]

rows_js = []
for etf, code, spot, month, K, cc, c, pc, p in data:
    exp = datetime.date.fromisoformat(expiries[month])
    days = max((exp - today).days, 1)
    F = c - p + K
    basis = F - spot
    basis_pct = basis / spot * 100
    annual = basis_pct * 365 / days
    rows_js.append(
        '{etf:"%s",etf_code:"%s",spot:%.3f,month:"%s",expiry:"%s",days:%d,strike:%.3f,'
        'call_code:"%s",call:%.4f,put_code:"%s",put:%.4f,synthetic:%.4f,basis:%.4f,basis_pct:%.4f,annual_pct:%.2f}' % (
            etf, code, spot, month, expiries[month], days, K, cc, c, pc, p, F, basis, basis_pct, annual))

rows_py = []
for etf, code, spot, month, K, cc, c, pc, p in data:
    exp = datetime.date.fromisoformat(expiries[month])
    days = max((exp - today).days, 1)
    F = c - p + K
    basis = F - spot
    basis_pct = basis / spot * 100
    annual = basis_pct * 365 / days
    rows_py.append(
        '{"etf":"%s","etf_code":"%s","spot":%.3f,"month":"%s","expiry":"%s","days":%d,"strike":%.3f,'
        '"call_code":"%s","call":%.4f,"put_code":"%s","put":%.4f,"synthetic":%.4f,"basis":%.4f,"basis_pct":%.4f,"annual_pct":%.2f}' % (
            etf, code, spot, month, expiries[month], days, K, cc, c, pc, p, F, basis, basis_pct, annual))

# ---------- 1. HTML FALLBACK ----------
html_path = 'etf_option_basis_dashboard.html'
with io.open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

html_new_rows = '  rows: [\n' + '\n'.join('    ' + r + ',' for r in rows_js) + '\n  ]\n};'
# 替换 source/updated_at 行 + rows 块
html = re.sub(r'var FALLBACK = \{\n  source:.*?\n  updated_at:.*?\n  rows:.*?\n\};',
              'var FALLBACK = {\n  source: "通达信 2026-08-14 收盘(兜底)",\n  updated_at: "2026-08-14 15:30",\n' + html_new_rows,
              html, count=1, flags=re.S)

with io.open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)
print('HTML updated, FALLBACK rows:', len(rows_js))

# ---------- 2. option_server.py FALLBACK_DATA ----------
py_path = 'option_server.py'
with io.open(py_path, 'r', encoding='utf-8') as f:
    py = f.read()

py_new_rows = '    "rows": [\n' + '\n'.join('        ' + r + ',' for r in rows_py) + '\n    ],\n}'
py = re.sub(r'FALLBACK_DATA = \{\n    "source":.*?\n    "updated_at":.*?\n    "rows":.*?\n\}',
            'FALLBACK_DATA = {\n    "source": "通达信 2026-08-14 收盘(兜底)",\n    "updated_at": "2026-08-14 15:30",\n' + py_new_rows,
            py, count=1, flags=re.S)

with io.open(py_path, 'w', encoding='utf-8') as f:
    f.write(py)
print('option_server.py updated, FALLBACK_DATA rows:', len(rows_py))
