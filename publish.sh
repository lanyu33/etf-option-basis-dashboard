#!/usr/bin/env bash
# publish.sh — 增量发布 ETF 期权合成期货贴水看板到 GitHub Pages
# 仓库: lanyu33/etf-option-basis-dashboard  (对齐 investment-workbench 的 main/root/index.html 格式)
#
# 用法:
#   bash publish.sh                          # 交互输入 PAT 后发布（沿用已有数据快照）
#   bash publish.sh --update                 # 发布前先拉取 Sina 实时行情，刷新 option_basis_data.json
#   GITHUB_TOKEN=ghp_xxx bash publish.sh     # 用环境变量里的 PAT 发布（不回显）
#   bash publish.sh "自定义提交信息"          # 自定义 commit message
#   bash publish.sh --update "刷新数据并发布" # 组合：先更新数据，再自定义信息提交
#
# 安全: PAT 仅用于本次 push 的临时 URL / Authorization 头，不写入 .git/config / 不写文件。
set -euo pipefail

cd "$(dirname "$0")"

REPO="lanyu33/etf-option-basis-dashboard"

# ---- 解析参数: --update 为开关, 其余作为 commit message ----
UPDATE=0
POS=()
for a in "$@"; do
  case "$a" in
    --update) UPDATE=1 ;;
    *) POS+=("$a") ;;
  esac
done
MSG="${POS[0]:-更新 ETF 期权贴水看板 ($(date +%Y-%m-%d))}"

# ---- 可选: 发布前重新拉取行情 ----
if [ "$UPDATE" = "1" ]; then
  echo "==> [0/4] 重新拉取行情数据 (Sina, 需联网) ..."
  if command -v python3 >/dev/null 2>&1; then
    PY=python3
  elif command -v python >/dev/null 2>&1; then
    PY=python
  else
    PY=python
  fi
  "$PY" update_data.py || echo "⚠️ 数据更新失败，将沿用已有 option_basis_data.json 继续发布"
fi

echo "==> 同步 Pages 入口 index.html (来自 etf_option_basis_dashboard.html)"
cp etf_option_basis_dashboard.html index.html

if [ -z "$(git status --porcelain)" ]; then
  echo "==> 没有改动，无需发布。退出。"
  exit 0
fi

echo "==> 暂存改动"
git add -A

echo "==> 提交: $MSG"
git commit -m "$MSG"

TOKEN="${GITHUB_TOKEN:-}"
if [ -z "$TOKEN" ]; then
  echo -n "==> 请输入 GitHub PAT (ghp_...，仅用于本次 push，不落盘): "
  read -r -s TOKEN
  echo
fi

echo "==> 推送到 main"
# 本机 Git  credential-manager 会干扰 URL 内 x-access-token，改用 Authorization 头注入放行
git -c "http.extraHeader=Authorization: Basic $(printf 'x-access-token:%s' "$TOKEN" | base64)" \
  push "https://github.com/${REPO}.git" main

echo ""
echo "✅ 发布完成。站点: https://lanyu33.github.io/etf-option-basis-dashboard/"
