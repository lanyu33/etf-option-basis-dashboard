# -*- coding: utf-8 -*-
"""
ETF 期权合成期货贴水 Dashboard 数据生成
数据来源: Wind 金融终端 (2026-08-12 收盘)
"""

# 原始数据 (Wind MCP 获取)
raw_data = [
    # 50ETF (510050.SH) 现价 3.043
    {"etf": "50ETF", "etf_code": "510050.SH", "spot": 3.043, "month": "8月", "expiry": "2026-08-26", "days": 14,
     "strike": 3.000, "call_code": "10011855.SH", "call": 0.0604, "put_code": "10011864.SH", "put": 0.0195},
    {"etf": "50ETF", "etf_code": "510050.SH", "spot": 3.043, "month": "9月", "expiry": "2026-09-23", "days": 42,
     "strike": 3.000, "call_code": "10010974.SH", "call": 0.0796, "put_code": "10010983.SH", "put": 0.0520},
    {"etf": "50ETF", "etf_code": "510050.SH", "spot": 3.043, "month": "12月", "expiry": "2026-12-23", "days": 133,
     "strike": 3.000, "call_code": "10011429.SH", "call": 0.1218, "put_code": "10011438.SH", "put": 0.1142},
    {"etf": "50ETF", "etf_code": "510050.SH", "spot": 3.043, "month": "2027年3月", "expiry": "2027-03-24", "days": 224,
     "strike": 3.000, "call_code": "10012166.SH", "call": 0.1503, "put_code": "10012175.SH", "put": 0.1531},

    # 300ETF (510300.SH) 现价 4.748
    {"etf": "300ETF", "etf_code": "510300.SH", "spot": 4.748, "month": "8月", "expiry": "2026-08-26", "days": 14,
     "strike": 4.700, "call_code": "10011870.SH", "call": 0.0821, "put_code": "10011879.SH", "put": 0.0450},
    {"etf": "300ETF", "etf_code": "510300.SH", "spot": 4.748, "month": "9月", "expiry": "2026-09-23", "days": 42,
     "strike": 4.700, "call_code": "10010993.SH", "call": 0.1225, "put_code": "10011002.SH", "put": 0.1032},
    {"etf": "300ETF", "etf_code": "510300.SH", "spot": 4.748, "month": "12月", "expiry": "2026-12-23", "days": 133,
     "strike": 4.700, "call_code": "10011446.SH", "call": 0.1833, "put_code": "10011455.SH", "put": 0.2218},
    {"etf": "300ETF", "etf_code": "510300.SH", "spot": 4.748, "month": "2027年3月", "expiry": "2027-03-24", "days": 224,
     "strike": 4.700, "call_code": "10012184.SH", "call": 0.2124, "put_code": "10012193.SH", "put": 0.3078},

    # 500ETF (510500.SH) 现价 8.053
    {"etf": "500ETF", "etf_code": "510500.SH", "spot": 8.053, "month": "8月", "expiry": "2026-08-26", "days": 14,
     "strike": 8.104, "call_code": "10011888.SH", "call": 0.1114, "put_code": "10011897.SH", "put": 0.2065},
    {"etf": "500ETF", "etf_code": "510500.SH", "spot": 8.053, "month": "9月", "expiry": "2026-09-23", "days": 42,
     "strike": 8.104, "call_code": "10011009.SH", "call": 0.2020, "put_code": "10011018.SH", "put": 0.3592},
    {"etf": "500ETF", "etf_code": "510500.SH", "spot": 8.053, "month": "12月", "expiry": "2026-12-23", "days": 133,
     "strike": 8.104, "call_code": "10011464.SH", "call": 0.3309, "put_code": "10011473.SH", "put": 0.6372},

    # 科创50ETF (588000.SH) 现价 1.833
    {"etf": "科创50ETF", "etf_code": "588000.SH", "spot": 1.833, "month": "8月", "expiry": "2026-08-26", "days": 14,
     "strike": 1.850, "call_code": "10012107.SH", "call": 0.0474, "put_code": "10012108.SH", "put": 0.0682},
]

# 计算合成期货和贴水
results = []
for d in raw_data:
    synthetic = d["call"] - d["put"] + d["strike"]
    basis = synthetic - d["spot"]
    basis_pct = basis / d["spot"] * 100
    annual_pct = basis_pct * 365 / d["days"]
    results.append({
        **d,
        "synthetic": round(synthetic, 4),
        "basis": round(basis, 4),
        "basis_pct": round(basis_pct, 4),
        "annual_pct": round(annual_pct, 2),
    })

# 输出 JSON
import json
print(json.dumps(results, ensure_ascii=False, indent=2))
