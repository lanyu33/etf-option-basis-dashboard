# -*- coding: utf-8 -*-
"""
生成静态快照版 Dashboard (用于 CloudStudio 部署)
读取 option_basis_data.json 最新数据, 嵌入独立 HTML, 输出到 dist/
"""
import json
import os
import re

BASE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(BASE, "etf_option_basis_dashboard.html")
DATA_FILE = os.path.join(BASE, "option_basis_data.json")
OUT_DIR = os.path.join(BASE, "dist")
OUT_HTML = os.path.join(OUT_DIR, "index.html")


def main():
    with open(TEMPLATE, "r", encoding="utf-8") as f:
        html = f.read()

    # 读取最新数据 (优先 json, 缺失则用模板内置兜底)
    snapshot = None
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            snapshot = json.load(f)

    if snapshot:
        data_json = json.dumps(snapshot, ensure_ascii=False)
        # 替换 FALLBACK 数据块
        pattern = re.compile(r"var FALLBACK = \{[\s\S]*?\n\};", re.MULTILINE)
        html, n = pattern.subn("var FALLBACK = " + data_json + ";", html, count=1)
        print("FALLBACK replaced:", n)

    # 1. loadData: 静态版直接用内嵌数据, 不 fetch
    html = re.sub(
        r"function loadData\(\) \{[\s\S]*?\n\}",
        "function loadData() {\n  applyData(FALLBACK);\n}",
        html, count=1)

    # 2. doRefresh: 静态版不支持在线刷新
    html = re.sub(
        r"function doRefresh\(\) \{[\s\S]*?\n\}",
        "function doRefresh() {\n  showToast('✗ 静态版不支持在线刷新，请在本地运行 option_server.py 或重新生成快照', false);\n}",
        html, count=1)

    # 3. startService: 静态版无本地服务
    html = re.sub(
        r"function startService\(\) \{[\s\S]*?\n\}",
        "function startService() {\n  showToast('✗ 静态版无本地服务，请下载源码本地运行 option_server.py', false);\n}",
        html, count=1)

    # 4. 更新标题备注
    html = html.replace("ETF 期权 合成期货贴水 Dashboard", "ETF 期权合成期货贴水 Dashboard（静态快照）")

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print("Written:", OUT_HTML, os.path.getsize(OUT_HTML), "bytes")


if __name__ == "__main__":
    main()
