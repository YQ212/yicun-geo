#!/usr/bin/env bash
# 一村科技 GEO 全流程一键运行（零依赖，无需任何密钥）
# 用法：bash run_all.sh
# 做了什么：① 生成今日选题文章 → ② 发布成可上线静态站 → ③ 生成当月回测清单
# 你（用户）唯一要做的：把文章上线（见末尾二选一）。
set -e
cd "$(dirname "$0")"
echo "==== 1/3 生成 GEO 文章（模板兜底，无需密钥）===="
python3 generate.py
echo "==== 2/3 发布静态站（output/ 含 index.html+sitemap+RSS）===="
python3 publish.py
echo "==== 3/3 生成月度回测清单（diagnosis/）===="
python3 diagnose.py
echo ""
echo "==================== 完成 ===================="
echo "接下来把内容上线（二选一，都无需技术/密钥）："
echo "  A. 最少技术（推荐）：把 output/<选题>/for-shop.md 的内容，复制粘贴到"
echo "     阿里国际站『公司简介』 + 1688 旺铺『公司介绍』。AI 会从这两大高频抓取源读到一村。"
echo "  B. 独立品牌站：把 config.json 的 site_url 改成真实域名，再 bash deploy_ghpages.sh <用户> <仓库>"
echo "本地预览：cd output && python3 -m http.server 8080"
