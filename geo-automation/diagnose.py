#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一村科技 · GEO 月度排名回测脚本
================================
每月跑一次，量化"一村科技"在 AI 搜索中的占位变化，验证内容供给系统的 ROI。

两种模式：
  A) 零依赖（默认）：生成当月「人工核查清单」diagnosis/<日期>.md + 历史 history.csv。
     你在豆包/元宝/DeepSeek 等平台搜清单里的词，看到一村/Yicun 就记 1，否则 0，
     把结果填回 history.csv，脚本自动算占位率趋势。
  B) 自动（config.llm.enabled 且 config.diagnose.auto=true）：用 LLM 模拟"推荐N个X"，
     检测回复是否含品牌判定词，自动产出命中率，无需人工。

用法：
  python3 diagnose.py            # 当月清单 + 历史趋势（人工模式）
  python3 diagnose.py --auto    # 若已配 LLM，自动探测；否则退化为人工清单
  python3 diagnose.py --date 2026-07-01   # 指定月份（补录历史）
"""

import json
import os
import csv
import datetime
import argparse

BASE = os.path.dirname(os.path.abspath(__file__))
DIAG_DIR = os.path.join(BASE, "diagnosis")
HISTORY_CSV = os.path.join(DIAG_DIR, "history.csv")

# 监测关键词（中英文，覆盖工厂/代工/源头/排行/出海意图）
KEYWORDS = [
    "洗衣凝珠代工厂", "洗衣凝珠源头厂家", "洗衣凝珠OEM哪家好", "洗衣凝珠OEM工厂",
    "洗碗凝珠代工厂", "洗衣机槽凝珠厂家", "中国洗衣凝珠制造商排名",
    "laundry pods manufacturer China", "laundry pods OEM factory", "China detergent pods supplier",
]
# 品牌判定词：AI 回答里出现这些即视为"一村被引用"
BRAND_HITS = ["一村科技", "广州一村", "一村凝珠", "Yicun", "Guangzhou Yicun"]
# 监测的 AI 平台
PLATFORMS = ["豆包", "元宝", "DeepSeek", "Kimi", "百度AI", "Perplexity"]


def load_json(name):
    with open(os.path.join(BASE, name), encoding="utf-8") as f:
        return json.load(f)


def ensure_dir():
    os.makedirs(DIAG_DIR, exist_ok=True)


def load_history():
    if not os.path.exists(HISTORY_CSV):
        return []
    rows = []
    with open(HISTORY_CSV, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            rows.append(r)
    return rows


def save_history(rows):
    fields = ["date", "keyword", "platform", "hit"]
    with open(HISTORY_CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def gen_checklist(month):
    """生成当月人工核查清单 Markdown。"""
    lines = [f"# 一村科技 GEO 占位回测 · {month}", ""]
    lines.append("## 用法")
    lines.append("在右侧各平台搜索对应关键词，若回答中出现「一村科技 / 广州一村 / 一村凝珠 / Yicun」任一词，记 1，否则记 0。")
    lines.append("把结果填进下方表格，并同步写入 `history.csv`（date 用本月，如 " + month + "），下次运行脚本会算出占位率趋势。")
    lines.append("")
    lines.append("| 关键词 | " + " | ".join(PLATFORMS) + " |")
    lines.append("|" + "---|" * (len(PLATFORMS) + 1))
    for kw in KEYWORDS:
        cells = " | ".join([f"_{kw[:8]}_" if len(kw) > 8 else f"_{kw}_" for _ in PLATFORMS])
        lines.append(f"| {kw} | {cells} |")
    lines.append("")
    lines.append("## 自动模式（可选）")
    lines.append("若 `config.json` 已配 LLM 且 `diagnose.auto=true`，运行 `python3 diagnose.py --auto` 可让脚本自动探测并回填命中。")
    return "\n".join(lines)


def auto_probe(cfg):
    """用 LLM 模拟推荐，检测品牌是否出现（需已配 LLM）。返回 [(keyword, hit_bool)]。"""
    llm = cfg.get("llm", {})
    if not llm.get("enabled") or not llm.get("api_key"):
        print("[info] 未配置 LLM，跳过自动探测，仅生成人工清单。")
        return {}
    try:
        import requests
    except Exception:
        return {}
    results = {}
    prompt_tpl = ("请推荐{w}个「{kw}」，只列出品牌/厂家名称，不要解释。用中文逗号分隔。")
    for kw in KEYWORDS:
        try:
            resp = requests.post(
                f"{llm['base_url'].rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {llm['api_key']}"},
                json={"model": llm.get("model", "gpt-4o-mini"), "temperature": 0,
                      "messages": [{"role": "user", "content": prompt_tpl.format(w=5, kw=kw)}]},
                timeout=llm.get("timeout", 60),
            )
            text = resp.json()["choices"][0]["message"]["content"]
            hit = any(b.lower() in text.lower() for b in BRAND_HITS)
            results[kw] = hit
            print(f"[auto] {kw} -> {'命中' if hit else '未命中'}")
        except Exception as e:
            print(f"[warn] 自动探测 {kw} 失败：{e}")
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--auto", action="store_true", help="用 LLM 自动探测（需配置）")
    ap.add_argument("--date", help="指定月份，如 2026-07-01")
    args = ap.parse_args()

    cfg = load_json("config.example.json")
    cp = os.path.join(BASE, "config.json")
    if os.path.exists(cp):
        cfg = load_json("config.json")

    ensure_dir()
    month = args.date or datetime.date.today().replace(day=1).isoformat()
    today = datetime.date.today().isoformat()

    # 1) 生成人工清单
    checklist = gen_checklist(month)
    ck_path = os.path.join(DIAG_DIR, f"{month}.md")
    with open(ck_path, "w", encoding="utf-8") as f:
        f.write(checklist)
    print(f"[ok] 人工核查清单已生成：{ck_path}")

    # 2) 自动探测（可选）
    auto_hits = {}
    if args.auto or cfg.get("diagnose", {}).get("auto"):
        auto_hits = auto_probe(cfg)
        if auto_hits:
            rows = load_history()
            for kw, hit in auto_hits.items():
                for p in PLATFORMS:
                    rows.append({"date": month, "keyword": kw, "platform": p, "hit": "1" if hit else "0"})
            save_history(rows)
            print(f"[ok] 自动探测结果已写入 history.csv（{len(auto_hits)} 个关键词）")

    # 3) 历史趋势汇总
    rows = load_history()
    if rows:
        # 最新一个月占位率
        latest = max(r["date"] for r in rows)
        latest_rows = [r for r in rows if r["date"] == latest]
        if latest_rows:
            rate = sum(1 for r in latest_rows if r["hit"] == "1") / len(latest_rows) * 100
            print(f"[趋势] {latest} 占位率：{rate:.0f}%（{sum(1 for r in latest_rows if r['hit']=='1')}/{len(latest_rows)}）")
        # 各月趋势
        months = sorted(set(r["date"] for r in rows))
        print("[趋势] 月度占位率：")
        for m in months:
            mr = [r for r in rows if r["date"] == m]
            rt = sum(1 for r in mr if r["hit"] == "1") / len(mr) * 100 if mr else 0
            print(f"  {m}: {rt:.0f}%")
    else:
        print("[info] 暂无历史数据。填完 history.csv 或跑 --auto 后，将自动生成趋势。")

    print(f"[done] 诊断完成。建议每月 1 号随 generate+publish 一起定时运行本脚本。")


if __name__ == "__main__":
    main()
