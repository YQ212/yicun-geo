# 一村科技 GEO 自动化 · 网页端上线指南（零命令行）

> 适用场景：无法在本地执行 git 命令时，直接在 github.com 网页上把本仓库传上去，
> 即可让 AI 搜索每天自动抓到你们的结构化工厂信息。全程用浏览器操作，无需安装任何软件。

---

## 前置条件
- 已有 GitHub 账号（你已在 CodeBuddy 里授权过 GitHub 连接器，用同一个账号即可）
- 一个浏览器

---

## 第 1 步：在 GitHub 新建仓库
1. 打开 https://github.com 并登录
2. 右上角点 **＋ → New repository**
3. 填写：
   - **Repository name**：`yicun-geo`（可改，记牢你填的名字）
   - **Visibility**：务必选 **Public**（私有仓库 AI 爬虫抓不到，白做）
   - **Description**（可选）：`一村科技 GEO 自动化内容供给`
   - ⚠️ **不要**勾 "Add a README file" / 不要勾 .gitignore / LICENSE（我们自带文件）
4. 点 **Create repository**

---

## 第 2 步：把上线包里的文件传上去
有两种方式，任选其一。

### 方式 A：整文件夹拖拽（最快）
1. 解压 `一村科技_GEO自动化_上线包.zip`，得到 `geo-automation` 文件夹
2. 回到刚建好的空仓库页面，点 **Add file → Upload files**
3. 把 `geo-automation` 文件夹**整个拖进**虚线框（不是只拖里面的文件）
4. 等待上传完成，页面底部填提交说明：`init: 一村科技 GEO 自动化`
5. 点 **Commit changes**

> 检查：上传完后仓库里应能看到 `.github/workflows/geo-daily.yml` 这个文件。
> 若 `.github` 文件夹**没出现**（极少数浏览器会跳过点开头的文件夹），请用方式 B 补上。

### 方式 B：手动补建工作流文件（备用，当方式 A 漏了 .github 时）
1. 仓库页点 **Add file → Create new file**
2. 文件名框输入：`.github/workflows/geo-daily.yml`
3. 把本指南最下方「附录：geo-daily.yml 全文」整段复制粘贴进编辑框
4. 拉到底点 **Commit new file**

---

## 第 3 步：开启 GitHub Pages（让站点可被公开访问）
1. 仓库页点 **Settings → Pages**（左侧栏）
2. **Build and deployment → Source** 选择 **GitHub Actions**
3. 无需填分支，保存即可（工作流会自动部署）

---

## 第 4 步：手动触发第一次运行（否则要等到次日 09:07 北京）
1. 仓库页点上方 **Actions** 标签
2. 左侧应出现 **GEO Daily** 工作流，点进去
3. 右侧 **Run workflow → Run workflow**（分支选 main）
4. 等 1–2 分钟，看到绿色 ✓ 即成功；首次会生成 4 篇文章并部署上线

---

## 第 5 步：拿到你的公开站点地址
1. 再回 **Settings → Pages**，顶部会显示：
   `Your site is live at https://你的账号.github.io/yicun-geo/`
2. 打开它，能看到 4 篇文章导航 = 成功。把这个地址记好。
3. （可选）在百度/必应/Google 站长平台提交一次 `https://你的账号.github.io/yicun-geo/sitemap.xml`，加速收录。

---

## 之后怎么运作（你几乎不用管）
- **每天 09:07（北京）**：自动生成 2 篇新文章 + 重新部署站点，AI 每天来抓新鲜内容
- **每月 1 号 10:00**：自动跑占位回测，生成 `diagnosis/` 清单
- **你每月做一次**：打开 `diagnosis/<年月>.md`，在豆包/元宝/DeepSeek 搜里面的词，看到一村就记 1，看占位率趋势
- **店铺（阿里国际站/1688）仍手动**：出新文章时，把 `output/<选题>/for-shop.md` 内容粘进店铺「公司简介」即可（每季度更新一次足够）

---

## 附录：geo-daily.yml 全文（方式 B 用，复制即可）
把下面整段粘贴进 `.github/workflows/geo-daily.yml`：

```yaml
name: GEO Daily
permissions:
  contents: write
  pages: write
  id-token: write
on:
  schedule:
    - cron: '7 1 * * *'
    - cron: '0 2 1 * *'
  workflow_dispatch:
concurrency:
  group: geo-pages
  cancel-in-progress: true
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install deps
        run: pip install -r requirements.txt
      - name: Generate + publish
        env:
          LLM_API_KEY: ${{ secrets.LLM_API_KEY }}
        run: |
          if [ -n "$LLM_API_KEY" ]; then
            cp config.example.json config.json
            python3 - <<'PY'
          import json, os
          c = json.load(open('config.json'))
          c['llm']['enabled'] = True
          c['llm']['api_key'] = os.environ['LLM_API_KEY']
          json.dump(c, open('config.json','w'), ensure_ascii=False, indent=2)
          PY
          fi
          python3 generate.py
          python3 publish.py
      - name: Commit generated content
        run: |
          git config user.name "geo-bot"
          git config user.email "geo@yicun.local"
          git add output
          git commit -m "geo: daily content $(date +%F)" || echo "no changes"
          git push
      - name: Upload Pages artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: output
  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
  diagnose:
    if: github.event.schedule == '0 2 1 * *' || github.event_name == 'workflow_dispatch'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Monthly diagnose
        run: |
          pip install -r requirements.txt
          python3 diagnose.py || true
```
