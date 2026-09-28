#!/usr/bin/env bash
# 一村科技 GEO 站点 · 一键部署到 GitHub Pages（免费、零 token、AI 必抓）
# ----------------------------------------------------------------------------
# 前置：有一个 GitHub 账号，并新建一个「公开仓库」（仓库名随意，如 yicun-geo）。
# 然后在仓库 Settings -> Pages -> Build and deployment 选 "Deploy from a branch"，
# 分支选本脚本推送的 master，目录选 /(root)。保存后约 1 分钟生效。
# 用法：
#   bash deploy_ghpages.sh <你的GitHub用户名> <仓库名>
# 例：
#   bash deploy_ghpages.sh yicun-tech yicun-geo
# 部署后公开地址： https://<用户名>.github.io/<仓库名>/
# 注意：部署前请在 config.json 把 site_url 改成上面的公开地址，再跑 generate+publish。
set -e
USER="$1"; REPO="$2"
[ -z "$USER" ] && { echo "用法: bash deploy_ghpages.sh <GitHub用户名> <仓库名>"; exit 1; }
cd "$(dirname "$0")"
rm -rf .deploy && mkdir -p .deploy
cp -r output/* .deploy/ 2>/dev/null || true
cd .deploy
git init -q
git checkout -q -b master 2>/dev/null || git checkout -q -B master
git remote remove origin 2>/dev/null || true
git remote add origin "https://github.com/$USER/$REPO.git"
git add -A
git commit -q -m "deploy GEO site $(date +%F-%T)" || echo "（无变更，跳过提交）"
git push -u origin master 2>&1 | tail -3
echo "✅ 部署完成 -> https://$USER.github.io/$REPO/"
echo "  记得在 百度/必应/Google 站长平台 提交一次 sitemap.xml 以加速收录。"
