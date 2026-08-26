# -*- coding: utf-8 -*-
"""用通达信 8/24 收盘数据更新 dashboard 三处数据:
1. option_basis_data.json (主数据 rows + etfs spot)
2. HTML FALLBACK (前端兜底)
3. option_server.py FALLBACK_DATA (服务端兜底)
"""
import datetime, json, re, io, sys

today = datetime.date(2026, 8, 24)
expiries = {'8月': '2026-08-26', '9月': '2026-09-23', '12月': '2026-12-23', '2027年3月': '2027-03-24'}

# (etf, code, spot, prev_close, month, K, call_code, call, put_code, put) — 通达信 8/24 收盘
data = [
    ('50ETF','510050.SH',2.979,2.993,'8月',3.000,'10011855.SH',0.0075,'10011864.SH',0.0289),
    ('50ETF','510050.SH',2.979,2.993,'9月',3.000,'10010974.SH',0.0368,'10010983.SH',0.0685),
    ('50ETF','510050.SH',2.979,2.993,'12月',3.000,'10011429.SH',0.0848,'10011438.SH',0.1431),
    ('50ETF','510050.SH',2.979,2.993,'2027年3月',3.000,'10012166.SH',0.1118,'10012175.SH',0.1871),
    ('300ETF','510300.SH',4.627,4.680,'8月',4.600,'10011869.SH',0.0428,'10011878.SH',0.0200),
    ('300ETF','510300.SH',4.627,4.680,'9月',4.600,'10010992.SH',0.0973,'10011001.SH',0.0980),
    ('300ETF','510300.SH',4.627,4.680,'12月',4.600,'10011445.SH',0.1639,'10011454.SH',0.2218),
    ('300ETF','510300.SH',4.627,4.680,'2027年3月',4.600,'10012183.SH',0.1927,'10012192.SH',0.3073),
    ('500ETF','510500.SH',7.740,7.866,'8月',7.750,'10012055.SH',0.0600,'10012064.SH',0.0842),
    ('500ETF','510500.SH',7.740,7.866,'9月',7.750,'10012073.SH',0.2030,'10012082.SH',0.3000),
    ('500ETF','510500.SH',7.740,7.866,'12月',7.750,'10012091.SH',0.3272,'10012100.SH',0.5944),
    ('500ETF','510500.SH',7.740,7.866,'2027年3月',7.750,'10012203.SH',0.3770,'10012212.SH',0.8089),
    ('科创50ETF','588000.SH',1.691,1.745,'8月',1.700,'10012153.SH',0.0201,'10012156.SH',0.0309),
    ('科创50ETF','588000.SH',1.691,1.745,'9月',1.700,'10011030.SH',0.0668,'10011039.SH',0.0902),
    ('科创50ETF','588000.SH',1.691,1.745,'12月',1.700,'10011486.SH',0.1199,'10011495.SH',0.1808),
    ('科创50ETF','588000.SH',1.691,1.745,'2027年3月',1.700,'10012253.SH',0.1553,'10012254.SH',0.2198),
]

rows = []
for etf, code, spot, pc, month, K, cc, c, ppc, p in data:
    exp = datetime.date.fromisoformat(expiries[month])
    days = max((exp - today).days, 1)
    F = round(c - p + K, 4)
    basis = round(F - spot, 4)
    basis_pct = round(basis / spot * 100, 4)
    annual_pct = round(basis_pct * 365 / days, 2)
    rows.append({
        'etf': etf, 'etf_code': code, 'spot': spot, 'month': month,
        'expiry': expiries[month], 'days': days, 'strike': K,
        'call_code': cc, 'call': c, 'put_code': ppc, 'put': p,
        'synthetic': F, 'basis': basis, 'basis_pct': basis_pct, 'annual_pct': annual_pct,
        'prev_close': pc,
    })

for r in rows:
    print('{:<10} {:<10} spot={:<6} K={:<6} C={:<7} P={:<7} F={:<8} basis={:<8} annual={}%'.format(
        r['etf'], r['month'], r['spot'], r['strike'], r['call'], r['put'], r['synthetic'], r['basis'], r['annual_pct']))

# ---------- 1. option_basis_data.json ----------
with io.open('option_basis_data.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

d['source'] = '通达信 2026-08-24 收盘'
d['updated_at'] = '2026-08-24 15:30'
sys.path.insert(0, '.')
import option_server as s
new_rows = []
for r in rows:
    und = r['etf_code'].replace('.SH', '')
    unit = s.contract_unit(und, r['strike'])
    r['unit'] = unit
    r['call_premium'] = round(r['call'] * unit, 2)
    r['put_margin'] = s.put_margin(r['prev_close'], r['strike'], r['put'], unit)
    r['margin_total'] = round(r['call_premium'] + r['put_margin'], 2)
    r.pop('prev_close', None)
    new_rows.append(r)
d['rows'] = new_rows

spot_map = {'510050.SH': 2.979, '510300.SH': 4.627, '510500.SH': 7.740, '588000.SH': 1.691}
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
              'var FALLBACK = {\n  source: "通达信 2026-08-24 收盘(兜底)",\n  updated_at: "2026-08-24 15:30",\n' + html_new_rows,
              html, count=1, flags=re.S)
with io.open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)
print('HTML FALLBACK updated')

py_path = 'option_server.py'
with io.open(py_path, 'r', encoding='utf-8') as f:
    py = f.read()
py_new_rows = '    "rows": [\n' + '\n'.join('        ' + r + ',' for r in rows_py) + '\n    ],\n}'
py = re.sub(r'FALLBACK_DATA = \{\n    "source":.*?\n    "updated_at":.*?\n    "rows":.*?\n\}',
            'FALLBACK_DATA = {\n    "source": "通达信 2026-08-24 收盘(兜底)",\n    "updated_at": "2026-08-24 15:30",\n' + py_new_rows,
            py, count=1, flags=re.S)
with io.open(py_path, 'w', encoding='utf-8') as f:
    f.write(py)
print('option_server.py FALLBACK_DATA updated')
