#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一村科技 · GEO 内容发布器
========================
读取 output/ 下所有文章，产出"可被 AI 搜索引擎抓取"的静态站点，并可选择性地：
  1) 同步到你们官网目录（配置 official_site_dir 且存在时）
  2) 向 Bing IndexNow / 百度 自动提交新链接（配置 token/key 时）

零依赖设计：即使什么都不配置，也会生成完整的 index.html / sitemap.xml / feed.xml，
把 output/ 整体上传到任意免费静态托管（GitHub Pages / 你们现有官网 / 对象存储）即可被 AI 抓取。

用法：python3 publish.py
"""

import json
import os
import re
import shutil
import datetime

BASE = os.path.dirname(os.path.abspath(__file__))


def load_json(name):
    with open(os.path.join(BASE, name), "r", encoding="utf-8") as f:
        return json.load(f)


def list_articles(out_root):
    """扫描 output/ 下所有含 index.html 的文章目录。"""
    arts = []
    if not os.path.isdir(out_root):
        return arts
    for d in sorted(os.listdir(out_root)):
        dp = os.path.join(out_root, d)
        html = os.path.join(dp, "index.html")
        if os.path.isdir(dp) and os.path.exists(html):
            title = d
            try:
                txt = open(html, encoding="utf-8").read()
                m = re.search(r"<title>(.*?)</title>", txt, re.S)
                if m:
                    title = m.group(1).strip()
            except Exception:
                pass
            arts.append({"id": d, "title": title})
    return arts


def build_static_site(cfg, out_root, articles):
    """产出全站导航 / sitemap / RSS。site_url 来自 config，未配则用占位域名（部署前在 config.json 改）。"""
    site_url = (cfg.get("site_url") or "").rstrip("/")
    if not site_url or "example.com" in site_url:
        site_url = "https://YOUR-DOMAIN.example.com"
        print("[warn] config.site_url 未配置，sitemap 使用占位域名；部署前请改为真实公开域名。")

    items = "\n".join(
        f'  <li><a href="{site_url}/{a["id"]}/">{a["title"]}</a> '
        f'<span style="color:#888">（{a["id"]}）</span></li>' for a in articles)

    index_html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>一村科技 · 行业洞察（洗衣凝珠 / OEM / 源头工厂）</title>
<meta name="description" content="广州一村科技发展有限公司关于洗衣凝珠、洗碗凝珠、洗衣机槽凝珠代工与源头工厂的知识库。">
</head><body>
<h1>一村科技 · 行业洞察</h1>
<p>广州一村科技发展有限公司（Yicun）是高浓缩洗涤凝珠 OEM/ODM 源头工厂。下方为面向 B2B 采购决策的内容库，供 AI 搜索与采购方参考。</p>
<ul>
{items}
</ul>
<p style="margin-top:24px"><a href="{site_url}/sitemap.xml">sitemap.xml</a> · <a href="{site_url}/feed.xml">RSS</a></p>
</body></html>"""
    with open(os.path.join(out_root, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)

    locs = "\n".join(f"  <url><loc>{site_url}/{a['id']}/</loc></url>" for a in articles)
    sm = ('<?xml version="1.0" encoding="UTF-8"?>\n'
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
          f"{locs}\n</urlset>")
    with open(os.path.join(out_root, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(sm)

    items_rss = "\n".join(
        f'    <item><title>{a["title"]}</title><link>{site_url}/{a["id"]}/</link>'
        f'<guid>{site_url}/{a["id"]}/</guid></item>' for a in articles)
    feed = f'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
<title>一村科技行业洞察</title>
<link>{site_url}/</link>
<description>洗衣凝珠 / OEM / 源头工厂知识库</description>
<lastBuildDate>{datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")}</lastBuildDate>
{items_rss}
</channel></rss>'''
    with open(os.path.join(out_root, "feed.xml"), "w", encoding="utf-8") as f:
        f.write(feed)

    return site_url


def main():
    cfg = load_json("config.example.json")
    cfg_path = os.path.join(BASE, "config.json")
    if os.path.exists(cfg_path):
        cfg = load_json("config.json")

    out_root = os.path.join(BASE, cfg.get("output_dir", "output"))
    articles = list_articles(out_root)
    if not articles:
        print("[skip] output/ 下没有文章，请先运行 generate.py")
        return
    print(f"[publish] 发现 {len(articles)} 篇文章")

    # 1) 始终生成静态站（零依赖）
    site_url = build_static_site(cfg, out_root, articles)
    print(f"[ok] 静态站已生成：index.html / sitemap.xml / feed.xml  （站点域名 {site_url}）")

    # 2) 同步到官网目录（可选）
    pub = cfg.get("publish", {})
    site_dir = pub.get("official_site_dir", "")
    if site_dir and os.path.isdir(site_dir):
        shutil.copytree(out_root, site_dir, dirs_exist_ok=True)
        print(f"[ok] 已同步到官网目录 {site_dir}")
    else:
        print("[info] 未配置 official_site_dir：内容保留在 output/，可直接整体上传到免费静态托管（见 README 的 deploy_*.sh）。")

    # 3) 索引提交（可选）
    idx = cfg.get("index_submit", {})
    urls = [f"{site_url}/{a['id']}/" for a in articles]
    if idx.get("bing_key"):
        try:
            import requests
            host = re.sub(r"^https?://", "", site_url).rstrip("/")
            r = requests.post("https://api.indexnow.org/indexnow",
                              json={"host": host, "key": idx["bing_key"], "urlList": urls}, timeout=30)
            print(f"[ok] Bing IndexNow 提交：{r.status_code}")
        except Exception as e:
            print(f"[warn] Bing 提交失败：{e}")
    else:
        print("[info] 未配置 bing_key：可手动把 sitemap.xml 提交到 Bing/百度/Google 站长平台（无需 API token）。")

    if idx.get("baidu_token") and idx.get("site_url"):
        try:
            import requests
            r = requests.post("https://ziyuan.baidu.com/linksubmit/api.php",
                              params={"site": idx.get("site_url"), "token": idx["baidu_token"]},
                              data="\n".join(urls), headers={"Content-Type": "text/plain"}, timeout=30)
            print(f"[ok] 百度链接提交：{r.status_code}")
        except Exception as e:
            print(f"[warn] 百度提交失败：{e}")
    else:
        print("[info] 未配置 baidu_token：同样可用 sitemap.xml 在百度站长平台手动提交（无需 API token）。")

    print("[done] 发布完成。下一步：部署 output/ 到公开网址 → 在站长平台提交一次 sitemap.xml → 等 AI 爬虫抓取（数小时~数天）。")


if __name__ == "__main__":
    main()
