# -*- coding: utf-8 -*-
"""
重新拉取 ETF 期权合成期货贴水数据，写入 option_basis_data.json
复用 option_server.py 的 refresh_data()（Sina 服务端接口，带合法 Referer，可正常返回）
用于 publish.sh --update / GitHub Actions 盘中自动刷新：发布前刷新已发布快照，
使 GitHub Pages 的「刷新」拿到最新数据。

Sina 接口偶发超时（尤其 GitHub 运行器网络），内置 3 次重试 + 递增退避。
"""
import json
import time

import option_server as srv

RETRIES = 3
BACKOFF = 5  # 秒，第 n 次重试等待 n*BACKOFF


def main():
    last_err = None
    for attempt in range(1, RETRIES + 1):
        try:
            print("==> 拉取 Sina 实时行情并计算贴水 (第 {}/{} 次) ...".format(attempt, RETRIES))
            data = srv.refresh_data()
            if not data.get("rows"):
                raise RuntimeError("refresh_data 返回空 rows，可能 Sina 接口异常或当日无交易")
            with open(srv.DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print("OK 已更新 option_basis_data.json")
            print("   时间:", data["updated_at"])
            print("   ETF 数:", len(data.get("etfs", [])), "| 平值行数:", len(data.get("rows", [])))
            return
        except Exception as e:  # noqa: BLE001 - 重试场景需要捕获全部异常
            last_err = e
            print("   ✗ 第 {} 次失败: {}".format(attempt, e))
            if attempt < RETRIES:
                time.sleep(BACKOFF * attempt)
    raise last_err if last_err else RuntimeError("未知错误")


if __name__ == "__main__":
    main()
