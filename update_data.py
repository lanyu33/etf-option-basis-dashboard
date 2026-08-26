# -*- coding: utf-8 -*-
"""
重新拉取 ETF 期权合成期货贴水数据，写入 option_basis_data.json
复用 option_server.py 的 refresh_data()（Sina 服务端接口，带合法 Referer，可正常返回）
用于 publish.sh --update：发布前刷新已发布快照，使 GitHub Pages 的“刷新”拿到最新数据。
"""
import json
import option_server as srv


def main():
    print("==> 拉取 Sina 实时行情并计算贴水 ...")
    data = srv.refresh_data()
    if not data.get("rows"):
        raise RuntimeError("refresh_data 返回空 rows，可能 Sina 接口异常或当日无交易")
    with open(srv.DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("✅ 已更新 option_basis_data.json")
    print("   时间:", data["updated_at"])
    print("   ETF 数:", len(data.get("etfs", [])), "| 平值行数:", len(data.get("rows", [])))


if __name__ == "__main__":
    main()
