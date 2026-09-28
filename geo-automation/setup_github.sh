#!/usr/bin/env bash
# 一村科技 GEO 自动化 · 一键上线到 GitHub（在「能访问 GitHub」的环境执行）
# 前置：已 git init 且已提交（本仓库已就绪）；二选一：
#   A. 本地已 `gh auth login`  → 直接 `bash setup_github.sh`
#   B. 有 GitHub 令牌          → `bash setup_github.sh yicun-geo ghp_你的令牌`
# 脚本会：建公开仓库 → 推送 → 开启 GitHub Pages → 触发首次流水线
set -e
cd "$(dirname "$0")"

REPO="${1:-yicun-geo}"
TOKEN="${GITHUB_TOKEN:-${2:-}}"

# 统一默认分支为 main（GitHub Pages / Actions 最佳分支）
git branch -M main

if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
  echo ">> 使用 gh（已登录）"
  LOGIN=$(gh api user --jq .login)
  gh repo create "$REPO" --public --description "一村科技 GEO 自动化内容供给" --source . --remote origin --push 2>/dev/null \
    || git push -u origin main
  gh api -X POST "/repos/$LOGIN/$REPO/pages" -f build_type=workflow 2>/dev/null || echo "(Pages 若未自动开启，请到 Settings→Pages 选 GitHub Actions)"
  gh workflow run geo-daily.yml --ref main 2>/dev/null || true
  echo "✅ 完成。站点：https://$LOGIN.github.io/$REPO/"
elif [ -n "$TOKEN" ]; then
  echo ">> 使用令牌"
  LOGIN=$(curl -s -H "Authorization: Bearer $TOKEN" https://api.github.com/user | python3 -c "import sys,json;print(json.load(sys.stdin)['login'])")
  echo "登录身份：$LOGIN"
  curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    https://api.github.com/user/repos \
    -d "{\"name\":\"$REPO\",\"private\":false,\"description\":\"一村科技 GEO 自动化内容供给\",\"auto_init\":false}" >/dev/null
  git remote remove origin 2>/dev/null || true
  git remote add origin "https://oauth2:$TOKEN@github.com/$LOGIN/$REPO.git"
  git push -u origin main
  curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    https://api.github.com/repos/$LOGIN/$REPO/pages -d '{"build_type":"workflow"}' >/dev/null \
    || echo "(Pages 若未自动开启，请到 Settings→Pages 选 GitHub Actions)"
  curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    https://api.github.com/repos/$LOGIN/$REPO/actions/workflows/geo-daily.yml/dispatches \
    -d '{"ref":"main"}' >/dev/null || true
  echo "✅ 完成。站点：https://$LOGIN.github.io/$REPO/"
else
  echo "用法："
  echo "  A. 先跑 'gh auth login'，再： bash setup_github.sh"
  echo "  B. 或带令牌：            bash setup_github.sh yicun-geo ghp_你的令牌"
  exit 1
fi
echo "之后每天 09:07（北京）自动生成+部署，每月 1 号自动回测。"
