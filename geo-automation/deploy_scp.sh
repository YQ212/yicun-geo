#!/usr/bin/env bash
# 一村科技 GEO 站点 · 部署到你们自己的服务器（有 SSH 即可，无需额外 token）
# ----------------------------------------------------------------------------
# 前置：一台可 SSH 访问的服务器，且已配置好静态网站（如 Nginx 指向某目录）。
# 用法：
#   bash deploy_scp.sh <user@host> <远程网站根目录>
# 例（把内容传到官网根目录下的 /geo/ 子目录）：
#   bash deploy_scp.sh root@www.gz-yicun.com /var/www/html/geo
# 部署后公开地址： https://你们的域名/geo/<选题>/
# 注意：部署前请在 config.json 把 site_url 改成 https://你们的域名/geo
set -e
TARGET="$1"; REMOTE_DIR="$2"
[ -z "$TARGET" ] && { echo "用法: bash deploy_scp.sh <user@host> <远程目录>"; exit 1; }
REMOTE_DIR="${REMOTE_DIR:-/var/www/html/geo}"
cd "$(dirname "$0")"
rsync -avz --delete output/ "$TARGET:$REMOTE_DIR/"
echo "✅ 已同步到 $TARGET:$REMOTE_DIR"
echo "  若首次部署，请在站长平台提交一次 sitemap.xml 加速收录。"
