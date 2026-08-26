#!/usr/bin/env bash
# publish.sh — 增量发布 ETF 期权合成期货贴水看板到 GitHub Pages
# 仓库: lanyu33/etf-option-basis-dashboard  (对齐 investment-workbench 的 main/root/index.html 格式)
#
# 前置步骤（本脚本不管数据，只管发布）:
#   1. 改完看板 -> 保存 etf_option_basis_dashboard.html
#   2. 或刷新数据 -> 跑对应 update_tdx_*.py (会更新 option_basis_data.json 与 HTML 内 FALLBACK)
#
# 用法:
#   bash publish.sh                          # 交互输入 PAT 后发布
#   GITHUB_TOKEN=ghp_xxx bash publish.sh     # 用环境变量里的 PAT 发布（不回显）
#   bash publish.sh "自定义提交信息"          # 自定义 commit message
#
# 安全: PAT 仅用于本次 push 的临时 URL，不写入 .git/config / 不写文件。
set -euo pipefail

cd "$(dirname "$0")"

REPO="lanyu33/etf-option-basis-dashboard"

echo "==> [1/4] 同步 Pages 入口 index.html (来自 etf_option_basis_dashboard.html)"
cp etf_option_basis_dashboard.html index.html

if [ -z "$(git status --porcelain)" ]; then
  echo "==> 没有改动，无需发布。退出。"
  exit 0
fi

echo "==> [2/4] 暂存改动"
git add -A

MSG="${1:-更新 ETF 期权贴水看板 ($(date +%Y-%m-%d))}"
echo "==> [3/4] 提交: $MSG"
git commit -m "$MSG"

TOKEN="${GITHUB_TOKEN:-}"
if [ -z "$TOKEN" ]; then
  echo -n "==> 请输入 GitHub PAT (ghp_...，仅用于本次 push，不落盘): "
  read -r -s TOKEN
  echo
fi

echo "==> [4/4] 推送到 main"
git push "https://x-access-token:${TOKEN}@github.com/${REPO}.git" main

echo ""
echo "✅ 发布完成。站点: https://lanyu33.github.io/etf-option-basis-dashboard/"
