# -*- coding: utf-8 -*-
"""用 Wind 最新数据更新 option_basis_data.json 的平值部分"""
import json
import datetime
import option_server as s

# Wind 现货价 (2026-08-13 13:42 盘中)
spots = {
    "510050": {"price": 3.063, "prev_close": 3.043},
    "510300": {"price": 4.778, "prev_close": 4.748},
    "510500": {"price": 8.110, "prev_close": 8.053},
    "588000": {"price": 1.863, "prev_close": 1.833},
}

# Wind 平值合约最新价 (etf -> [(month, strike, call, put), ...])
wind_atm = {
    "50ETF": [
        ("8月", 3.1, 0.0159, 0.0596),
        ("9月", 3.1, 0.0386, 0.0987),
        ("12月", 3.1, 0.0835, 0.1625),
        ("2027年3月", 3.1, 0.1149, 0.2042),
    ],
    "300ETF": [
        ("8月", 4.8, 0.0390, 0.0789),
        ("9月", 4.8, 0.0800, 0.1406),
        ("12月", 4.8, 0.1506, 0.2621),
        ("2027年3月", 4.8, 0.1892, 0.3550),
    ],
    "500ETF": [
        ("8月", 8.0, 0.1760, 0.1215),
        ("9月", 8.0, 0.2605, 0.2697),
        ("12月", 8.0, 0.3799, 0.5467),
        ("2027年3月", 8.0, 0.4443, 0.7490),
    ],
    "科创50ETF": [
        ("8月", 1.85, 0.0581, 0.0516),
        ("9月", 1.85, 0.0948, 0.0990),
        ("12月", 1.85, 0.1546, 0.1867),
        ("2027年3月", 1.85, 0.1917, 0.2453),
    ],
}

underlying_map = {"50ETF": "510050", "300ETF": "510300", "500ETF": "510500", "科创50ETF": "588000"}

d = json.load(open("option_basis_data.json", encoding="utf-8"))

today = datetime.date.today()

# 更新 rows (平值16行)
new_rows = []
for etf_name, entries in wind_atm.items():
    und = underlying_map[etf_name]
    spot = spots[und]["price"]
    pc = spots[und]["prev_close"]
    for month, K, cp, pp in entries:
        # 从旧 rows 找对应的 expiry/days/codes
        old = next((r for r in d["rows"] if r["etf"] == etf_name and r["month"] == month), None)
        if old is None:
            continue
        synthetic = round(cp - pp + K, 4)
        basis = round(synthetic - spot, 4)
        basis_pct = round(basis / spot * 100, 4)
        days = old["days"]
        annual_pct = round(basis_pct * 365 / days, 2)
        unit = s.contract_unit(und, K)
        call_premium = round(cp * unit, 2)
        pm = s.put_margin(pc, K, pp, unit)
        margin_total = round(call_premium + pm, 2)
        new_rows.append({
            "etf": etf_name, "etf_code": old["etf_code"], "spot": round(spot, 4),
            "month": month, "expiry": old["expiry"], "days": days, "strike": K,
            "call_code": old["call_code"], "call": cp,
            "put_code": old["put_code"], "put": pp,
            "synthetic": synthetic, "basis": basis, "basis_pct": basis_pct, "annual_pct": annual_pct,
            "unit": unit, "call_premium": call_premium, "put_margin": pm, "margin_total": margin_total,
        })

# 更新 etfs 的 spot + 平值行价格 + atm 标记
for e in d["etfs"]:
    und = underlying_map.get(e["name"])
    if und and und in spots:
        e["spot"] = round(spots[und]["price"], 4)
    atm_map = {m: (K, cp, pp) for m, K, cp, pp in wind_atm.get(e["name"], [])}
    for m in e["months"]:
        # 先清除旧的 atm 标记
        for st in m["strikes"]:
            st["atm"] = False
        # 给新的平值行打标记并更新价格
        if m["month"] in atm_map:
            K, cp, pp = atm_map[m["month"]]
            for st in m["strikes"]:
                if abs(st["strike"] - K) < 1e-6:
                    spot = spots[und]["price"]
                    pc = spots[und]["prev_close"]
                    synthetic = round(cp - pp + K, 4)
                    basis = round(synthetic - spot, 4)
                    basis_pct = round(basis / spot * 100, 4)
                    annual_pct = round(basis_pct * 365 / m["days"], 2)
                    unit = s.contract_unit(und, K)
                    st["atm"] = True
                    st["call"] = cp
                    st["put"] = pp
                    st["synthetic"] = synthetic
                    st["basis"] = basis
                    st["basis_pct"] = basis_pct
                    st["annual_pct"] = annual_pct
                    st["unit"] = unit
                    st["call_premium"] = round(cp * unit, 2)
                    st["put_margin"] = s.put_margin(pc, K, pp, unit)
                    st["margin_total"] = round(st["call_premium"] + st["put_margin"], 2)

d["rows"] = new_rows
d["source"] = "Wind 金融终端 (盘中)"
d["updated_at"] = "2026-08-13 13:42"

json.dump(d, open("option_basis_data.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("已更新 rows:", len(new_rows), "行")
print("source:", d["source"], "updated:", d["updated_at"])
for r in new_rows:
    print("  {} {} K={} C={} P={} synth={} annual={}% margin={}".format(
        r["etf"], r["month"], r["strike"], r["call"], r["put"], r["synthetic"], r["annual_pct"], r["margin_total"]))
