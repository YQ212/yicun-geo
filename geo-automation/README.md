# 一村科技 · AI搜索（GEO）自动化内容供给系统

把"持续提升 AI 搜索排名"变成一条**每天自动运行**的流水线：自动生成对 AI 友好的结构化文章（洗衣凝珠代工厂 / OEM / 源头厂家等 B2B 决策词），铺到公开网址并被搜索引擎抓取，从而被豆包、元宝、DeepSeek、Kimi、百度 AI、ChatGPT、Perplexity 在回答中引用。

> 配套策略文档见 `/workspace/一村科技_AI搜索排名诊断与GEO提升方案.md`

---

## 0. 先回答：LLM 密钥 / 官网地址 / 收录 token 都没有，能跑吗？

**能。** 这三个里只有「LLM 密钥」影响文章文采，另两个都有免费替代方案。系统默认就是零依赖设计：

| 你缺的东西 | 是不是必须 | 没有时的替代方案 |
|-----------|-----------|----------------|
| **LLM 密钥** | 否 | 生成器自动用「模板兜底」产出**纯事实结构化文章**（已带 Schema 标记，AI 照样能抓）。质量可用，只是不如 LLM 润色后自然。 |
| **官网发布地址** | 否 | 用免费静态托管拿到公开网址：GitHub Pages（只要账号）、你们现有官网目录、或任意对象存储。本系统产出的是标准静态站。 |
| **百度/Bing 收录 token** | 否 | 把生成的 `sitemap.xml` 在百度/必应/Google 站长平台**手动提交一次**即可（只需验证你拥有该域名，**不需要 API token**）。Bing IndexNow 的 key 也能自己生成 UUID，非申请制。 |

> 结论：**现在就能跑通全流程并上线**；三个东西是"锦上添花"，有了更快更好，没有也不阻塞。

---

## 1. 一键跑通（真正零配置）

```bash
cd geo-automation
pip install -r requirements.txt
python3 generate.py          # 用模板兜底生成 2 篇（无需任何密钥）
python3 publish.py           # 产出完整静态站 output/（index.html + sitemap.xml + feed.xml）
```

跑完 `output/` 下就是一套可上线的站点。本地预览：

```bash
cd output && python3 -m http.server 8080   # 浏览器打开 http://localhost:8080
```

---

## 2. 上线到公开网址（三选一，均无需 token）

**A. GitHub Pages（最省事，免费）** — 需一个 GitHub 账号
1. 在 `config.json` 把 `site_url` 设为 `https://<用户名>.github.io/<仓库名>`
2. 重跑 `generate.py` + `publish.py`
3. `bash deploy_ghpages.sh <用户名> <仓库名>`

**B. 你们现有官网目录** — 需有服务器 SSH 或让运维上传
1. 在 `config.json` 把 `site_url` 设为真实域名（如 `https://www.gz-yicun.com/geo`）
2. 重跑 generate + publish
3. `bash deploy_scp.sh <user@host> <远程目录>`  （或把 `output/` 整目录交给网站维护方）

**C. 对象存储静态网站**（腾讯云 COS / 阿里 OSS / Cloudflare R2）— 需对应云账号
把 `output/` 整目录上传到存储桶并开启"静态网站托管"，`site_url` 填分配的访问域名。

**上线后必做一步（无 token）**：在百度搜索资源平台、Bing Webmaster、Google Search Console 分别添加该站点、验证所有权、提交 `sitemap.xml`。提交一次后，新文章靠 sitemap 自动被发现。

---

## 3. 三个东西到底怎么获取（想要"更快更好"时）

**① LLM 密钥（提升文采，可选）**
- 任意兼容 OpenAI 接口的服务商注册即可拿到一串 API Key，免费额度通常够每天 2 篇：
  - 国内：硅基流动（siliconflow.cn）、阿里云百炼、DeepSeek 开放平台、智谱/月之暗面等
  - 海外：OpenAI、Together、Groq 等
- 填入 `config.json`：`"llm": {"enabled": true, "base_url": "...", "api_key": "你的key", "model": "..."}`
- 不填 = 始终用模板兜底，不影响运行。

**② 官网发布地址（让内容有归处，可选）**
- 如果你们已有官网（如 gz-yicun.com）：让运维开一个 `/geo` 或 `/blog` 目录即可对接 B 方案。
- 如果没有官网：直接用 A 方案 GitHub Pages，零成本且 AI 抓取友好。

**③ 百度/Bing 收录 token（加速收录，可选）**
- **Bing IndexNow**：不是"申请 token"。你在 `config.json` 填一个自己生成的 UUID 作为 `bing_key`，并在站点根目录放一个 `<该UUID>.txt` 文件（内容为 UUID）即可，发布器会自动 POST。无 key 也能靠 sitemap 自然收录。
- **百度自动提交**：在百度搜索资源平台「链接提交 → 自动提交」里会得到一串 token，填 `baidu_token` 即可自动提交。不填也可在站长平台手动提交 sitemap（无需 token）。

---

## 4. 系统怎么工作

```
content_plan.json  ──┐
brand_facts.json   ──┼─► generate.py ─► output/<选题>/index.html (含 FAQPage/Article/Organization JSON-LD)
config.json        ──┘                  output/sitemap.xml, feed.xml, manifest.json
                                              │
                                              ▼
                                         publish.py
                                    ├─ 生成静态站（首页/站点地图/RSS）← 零依赖必做
                                    ├─ 同步官网目录（可选）
                                    └─ 提交 Bing/百度索引（可选）
```

- **轮转选题**：`state.json` 记录游标，每次生成 `schedule.per_run` 篇，各关键词簇均匀覆盖。
- **防幻觉**：提示词强制"只引用 brand_facts"，模板模式更是纯事实拼接。
- **对 AI 友好**：每篇自带 Schema 标记（FAQPage 是 AI 回答最高频引用的形态）。

## 5. 定时运行（三选一，见 `scheduler/`）

- `crontab.txt`：复制到 `crontab -e`，每天自动跑。
- `github_actions.yml`：推到 GitHub，免费云端每天跑并回传内容（配合 A 方案最省心）。
- `systemd_timer.md`：放公司服务器，带日志与失败重试。

## 6. 加新选题

编辑 `content_plan.json` 的 `topics` 数组加一条：

```json
{"id":"xxx","cluster":"工厂/代工词","type":"guide","keyword":"你的关键词",
 "title":"标题含关键词","intent":"采购","priority":"high",
 "faqs":[{"q":"问题","a":"用brand_facts里的事实作答"}]}
```

下次定时运行自动纳入轮转。

## 7. 怎么验证有效

每月用 AI 搜索诊断方法（见主方案文档第七节）测一次"洗衣凝珠代工厂""洗衣凝珠OEM哪家好"等词在豆包/元宝/DeepSeek 的占位，对比 `output/manifest.json` 的增长，即可量化 ROI。
