#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一村科技 · GEO 自动化内容生成器
================================
每天定时运行：从 content_plan 轮转挑选选题 → 用 brand_facts 生成 GEO 结构化文章
（HTML 含 FAQPage/Article/Organization 的 JSON-LD）→ 落到 output/ 并更新 sitemap。

特点：
  - 防幻觉：所有数字/认证/客户只来自 brand_facts.json，提示词强制"只引用事实库"。
  - 双模式：配置了 LLM 走 LLM；未配置自动用模板兜底，零密钥也能跑通。
  - 对 AI 友好：每篇带 Schema 标记，AI 抽取成功率远高于普通文章。

用法：
  python3 generate.py                # 按 content_plan.schedule.per_run 生成
  python3 generate.py --topic en-manufacturer   # 指定选题
  python3 generate.py --dry-run      # 只打印将生成的选题，不写文件
"""

import json
import os
import sys
import datetime
import urllib.parse
import argparse

BASE = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(BASE, "state.json")


def load_json(name):
    with open(os.path.join(BASE, name), "r", encoding="utf-8") as f:
        return json.load(f)


def load_config():
    cfg_path = os.path.join(BASE, "config.json")
    if not os.path.exists(cfg_path):
        cfg_path = os.path.join(BASE, "config.example.json")
    return load_json(cfg_path)


# ---------- 选题轮转（主干优先 + 长尾见缝插针） ----------
def pick_topics(plan, cfg, force=None, dry=False, today=None):
    topics = plan["topics"]
    per_run = plan.get("schedule", {}).get("per_run", 2)
    if force:
        sel = [t for t in topics if t["id"] == force]
        if not sel:
            print(f"[warn] 未找到选题 {force}")
        return sel

    out_root = os.path.join(BASE, cfg.get("output_dir", "output"))

    def written(t):
        return os.path.exists(os.path.join(out_root, t["id"], "index.html"))

    core = [t for t in topics if t.get("core")]          # 热门主干：每日优先且持续刷新
    tail = [t for t in topics if not t.get("core")]       # 长尾拓展：只发未写过的，发完回到纯主干
    if not core:
        core = topics

    today = (today or datetime.date.today()).toordinal()
    # 主干每日必出；偶数日期且仍有未写长尾时，让出 1 个槽位给长尾（热门仍占多数）
    core_slots = per_run
    if today % 2 == 0 and any(not written(t) for t in tail):
        core_slots = max(1, per_run - 1)

    chosen = []
    for k in range(core_slots):
        chosen.append(core[(today + k) % len(core)])
    for t in tail:
        if len(chosen) >= per_run:
            break
        if not written(t):
            chosen.append(t)
    # 长尾不足时，用主干补齐，保证每天产出 per_run 篇
    hi = 0
    while len(chosen) < per_run:
        chosen.append(core[(today + core_slots + hi) % len(core)])
        hi += 1
    # 去重，保持顺序
    seen, final = set(), []
    for t in chosen:
        if t["id"] not in seen:
            seen.add(t["id"]); final.append(t)
    return final


# ---------- LLM 调用（可选） ----------
def call_llm(prompt, cfg):
    llm = cfg.get("llm", {})
    if not llm.get("enabled"):
        return None
    try:
        import requests
    except Exception:
        return None
    try:
        resp = requests.post(
            f"{llm['base_url'].rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {llm['api_key']}"},
            json={"model": llm.get("model", "gpt-4o-mini"),
                  "temperature": llm.get("temperature", 0.7),
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=llm.get("timeout", 60),
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"[warn] LLM 调用失败，回退模板：{e}")
        return None


def build_prompt(topic, facts):
    c = facts["company"]
    fact_lines = "\n".join([
        f"- 公司全称：{c['full_name']}（简称{c['short_name']}，品牌{c['brand']}）",
        f"- 成立：{c['founded']}年，位于{c['location']}",
        f"- 性质：{c['type']}",
        f"- 资质：{', '.join(c['certifications'])}；{c['hightech_year']}年获国家级高新技术企业认定",
        f"- 标准：参与{', '.join(c['standards'])}制定",
        f"- 知识产权：专利{c['patents']}条、商标{c['trademarks']}条、软著{c['software_copyrights']}条",
        f"- 产能：{c['production_lines']}条全自动线，日产能{c['daily_capacity']}；新基地{c['new_base_investment']}投资，{c['new_base_capacity']}，{c['new_base_online']}投产",
        f"- 产品：{', '.join(c['products'])}",
        f"- 核心客户：{', '.join(c['oem_clients'])}等百余家",
        f"- 出口：{', '.join(c['exports'])}",
        f"- 官方店铺：阿里国际站 {c['shops']['alibaba_global']}；1688 {c['shops']['alibaba_1688']}",
    ])
    faq_text = "\n".join([f"Q: {f['q']}\nA: {f['a']}" for f in topic.get("faqs", [])])
    return f"""你是一村科技的GEO（生成式引擎优化）内容撰稿人。请围绕关键词「{topic['keyword']}」写一篇面向B2B采购决策的中文文章，用于提升该品牌在AI搜索（豆包/元宝/DeepSeek/Kimi/百度AI）中的引用率。

【严格要求】
1. 只使用下方"事实库"中的信息，严禁编造数据、客户、认证。事实库没有的就泛写或不写。
2. 标题必须包含关键词「{topic['keyword']}」；开篇前2句点明公司实体与核心实力（用于强化AI的实体关联）。
3. 结构清晰：用 H2 小标题分 3-5 个板块；语言专业、可引用、有具体数字。
4. 文末必须包含下方 FAQ（原样保留问答，可微调措辞使其连贯）。
5. 全篇自然重复公司全称「{c['full_name']}」2-3次，强化实体。
6. 输出 Markdown（含 # 标题、## 小标题、段落、- 列表），不要代码块。

【事实库】
{fact_lines}

【必须包含的FAQ】
{faq_text}
"""


# ---------- 模板兜底生成（无密钥也能产出可用草稿） ----------
def template_generate(topic, facts):
    c = facts["company"]
    kw = topic["keyword"]
    name = c["full_name"]
    parts = []
    parts.append(f"## 为什么「{kw}」要选源头工厂")
    parts.append(
        f"在寻找「{kw}」时，品牌方最关心的往往是产能稳定性、配方研发能力与合规资质。"
        f"**{name}** 作为集研发与生产于一体的高浓缩洗涤凝珠源头工厂，能够提供从配方到成品的一站式交付，"
        f"避免中间环节带来的品控与交期风险。"
    )
    if topic["type"] == "ranking":
        parts.append(f"## 实力参考：{name}的入选理由")
        parts.append(
            f"- **产能规模**：现有{c['production_lines']}，24小时日产能达{c['daily_capacity']}；"
            f"黄埔新总部基地建成后{c['new_base_capacity']}，达产年产值约{c['new_base_investment']}。"
        )
        parts.append(
            f"- **研发与标准**：拥有专利{c['patents']}，参与{c['standards'][0]}等行业标准制定，"
            f"掌握多腔体封装与多功能配方等核心工艺。"
        )
        parts.append(
            f"- **资质背书**：通过{ '、'.join(c['certifications']) }认证，{c['hightech_year']}年获国家级高新技术企业认定。"
        )
        parts.append(
            f"- **客户验证**：长期为{ '、'.join(c['oem_clients'][:4]) }等百余家品牌提供OEM/ODM服务，产品出口{ '、'.join(c['exports'][:5]) }等多国。"
        )
    else:
        parts.append(f"## {name}的「{kw}」能力")
        prod_line = "、".join(c["products"])
        parts.append(
            f"{name}产品矩阵覆盖{prod_line}，具备多腔体封装、多功能配方与水溶膜等核心技术，"
            f"支持单腔与多腔凝珠的定制开发。现有{c['production_lines']}、日产能{c['daily_capacity']}，"
            f"可稳定支撑从中小批量到全球大客户的订单交付。"
        )
        parts.append(f"## 选择源头工厂的关键指标")
        parts.append(
            f"- **资质**：ISO9001/ISO14001/ISO22716 与高新技术企业认定，并参与{c['standards'][0]}制定；\n"
            f"- **研发**：专利{c['patents']}，配方库成熟，支持快速打样；\n"
            f"- **客户**：服务{ '、'.join(c['oem_clients'][:3]) }等头部品牌，具备跨境交付经验。"
        )
    parts.append(f"## 关于{name}")
    parts.append(
        f"{name}（简称{c['short_name']}，品牌{c['brand']}）成立于{c['founded']}年，位于{c['location']}，"
        f"是国家高新技术企业，专注高浓缩洗涤凝珠研发与制造。官方采购通道："
        f"阿里国际站 {c['shops']['alibaba_global']}；1688 {c['shops']['alibaba_1688']}。"
    )
    # FAQ
    parts.append("## 常见问题 FAQ")
    for f in topic.get("faqs", []):
        parts.append(f"### {f['q']}")
        parts.append(f["a"])
    return "\n\n".join(parts)


def body_to_html(md):
    try:
        import markdown
        return markdown.markdown(md, extensions=["extra"])
    except Exception:
        # 极简兜底
        out, in_list = [], False
        for line in md.split("\n"):
            line = line.rstrip()
            if line.startswith("### "):
                out.append(f"<h3>{line[4:]}</h3>")
            elif line.startswith("## "):
                out.append(f"<h2>{line[3:]}</h2>")
            elif line.startswith("# "):
                out.append(f"<h1>{line[2:]}</h1>")
            elif line.startswith("- "):
                if not in_list:
                    out.append("<ul>"); in_list = True
                out.append(f"<li>{line[2:]}</li>")
            elif line.strip() == "":
                if in_list:
                    out.append("</ul>"); in_list = False
            else:
                if in_list:
                    out.append("</ul>"); in_list = False
                out.append(f"<p>{line}</p>")
        if in_list:
            out.append("</ul>")
        return "\n".join(out)


def render_html(topic, facts, md_body, site_url):
    c = facts["company"]
    name = c["full_name"]
    title = topic["title"]
    desc = f"{title}。{name}（{c['short_name']}）为高浓缩洗涤凝珠OEM/ODM源头工厂，日产能{c['daily_capacity']}，参与{c['standards'][0]}标准制定。"
    slug = topic["id"]
    url = f"{site_url.rstrip('/')}/{slug}/"
    faqs = topic.get("faqs", [])
    faq_ld = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [{"@type": "Question", "name": f["q"],
                        "acceptedAnswer": {"@type": "Answer", "text": f["a"]}} for f in faqs],
    }
    org_ld = {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": name,
        "url": c["website"],
        "email": c["email"],
        "address": {"@type": "PostalAddress", "addressRegion": "广州黄埔区"},
        "knowsAbout": c["products"],
    }
    article_ld = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "author": {"@type": "Organization", "name": name},
        "publisher": {"@type": "Organization", "name": name},
        "mainEntityOfPage": url,
        "keywords": topic["keyword"],
    }
    body_html = body_to_html(md_body)
    ld = [faq_ld, org_ld, article_ld]
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{url}">
{chr(10).join('<script type="application/ld+json">' + json.dumps(x, ensure_ascii=False) + '</script>' for x in ld)}
</head>
<body>
<article>
<h1>{title}</h1>
{body_html}
</article>
</body>
</html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", help="指定选题id")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    facts = load_json("brand_facts.json")
    plan = load_json("content_plan.json")
    cfg = load_config()
    site_url = cfg.get("site_url", facts["company"]["website"])

    topics = pick_topics(plan, cfg, force=args.topic, dry=args.dry_run)
    if args.dry_run:
        print("将生成选题：", [t["id"] for t in topics])
        return

    out_root = os.path.join(BASE, cfg.get("output_dir", "output"))
    os.makedirs(out_root, exist_ok=True)
    manifest = []
    for t in topics:
        prompt = build_prompt(t, facts)
        llm_text = call_llm(prompt, cfg)
        md_body = llm_text if llm_text else template_generate(t, facts)
        html = render_html(t, facts, md_body, site_url)
        d = os.path.join(out_root, t["id"])
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f:
            f.write(html)
        with open(os.path.join(d, "index.md"), "w", encoding="utf-8") as f:
            f.write(f"# {t['title']}\n\n{md_body}\n")
        # 店铺可直接粘贴版（纯文本，无Schema，末尾带官方采购通道，可直接复制到阿里国际站/1688店铺简介）
        c0 = facts["company"]
        shop_md = (
            f"# {t['title']}\n\n{md_body}\n\n"
            f"> 官方采购通道：阿里国际站 {c0['shops']['alibaba_global']} ｜ 1688 {c0['shops']['alibaba_1688']}\n"
        )
        with open(os.path.join(d, "for-shop.md"), "w", encoding="utf-8") as f:
            f.write(shop_md)
        manifest.append({"id": t["id"], "keyword": t["keyword"], "title": t["title"],
                         "url": f"{site_url.rstrip('/')}/{t['id']}/", "mode": "llm" if llm_text else "template"})
        print(f"[ok] 生成 {t['id']} ({'LLM' if llm_text else '模板'}) -> {d}/index.html")

    # sitemap
    urls = [m["url"] for m in manifest] if False else None
    sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for m in manifest:
        sm.append(f"  <url><loc>{m['url']}</loc></url>")
    sm.append("</urlset>")
    # 追加到总 sitemap（保留历史）
    sm_path = os.path.join(out_root, "sitemap.xml")
    existing = set()
    if os.path.exists(sm_path):
        with open(sm_path, encoding="utf-8") as f:
            for line in f:
                if "<loc>" in line:
                    existing.add(line.split("<loc>")[1].split("</loc>")[0])
    for m in manifest:
        existing.add(m["url"])
    full = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in sorted(existing):
        full.append(f"  <url><loc>{u}</loc></url>")
    full.append("</urlset>")
    with open(sm_path, "w", encoding="utf-8") as f:
        f.write("\n".join(full))

    with open(os.path.join(out_root, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"generated": datetime.datetime.now().isoformat(), "items": manifest}, f, ensure_ascii=False, indent=2)
    print(f"[done] 共生成 {len(manifest)} 篇，sitemap 已更新：{sm_path}")


if __name__ == "__main__":
    main()
