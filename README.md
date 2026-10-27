# 星辰 · 技术与研究

一个内容优先的中文技术博客，用于 AI 深度研究报告、技术实践、学习笔记和个人思考。基于 MkDocs Material、GitHub Actions 与 GitHub Pages，适合长期维护与 Markdown 写作。

- **博客**：https://zxingchen77.github.io/tech-notes/
- **仓库**：https://github.com/zxingchen77/tech-notes
- **部署记录**：https://github.com/zxingchen77/tech-notes/actions

## 功能

中文全文搜索（jieba 分词）、自动文章列表/分类/年份归档/标签、文章发布日期与更新日期、标题锚点与目录、明暗切换、移动端导航、代码高亮与复制。使用系统字体，无需请求 Google Fonts。已发布作者提供的研究文章，并保留一篇标注为示例的写作演示。

## 本地预览

需要 Python 3.12 与 Git：

```bash
git clone https://github.com/zxingchen77/tech-notes.git
cd tech-notes
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m mkdocs serve
```

打开终端给出的本地地址。Windows PowerShell 使用 `.venv\Scripts\Activate.ps1` 激活环境。

## 文件夹自动发布（macOS）

本机已配置监听博客仓库的上一级文件夹。将新文章保存为 Markdown，文件稳定两分钟后，脚本自动补齐文章元数据、严格构建、提交并推送，由 GitHub Actions 部署。电脑需要登录并联网。以 `_` 开头的草稿不会发布；已经登记的文章不重复导入。

安装、停止及排查见 [自动发布指南](docs/guides/auto-publish.md)。

## 发布一篇文章

1. 复制 [`templates/article.md`](templates/article.md) 到 `docs/blog/posts/` 下的分类目录。
2. 修改标题、日期、唯一 `slug`、分类和标签，写摘要与正文，填写 AI 参与和核查状态。
3. 将 `draft: true` 改为 `draft: false`。
4. 运行 `python -m mkdocs build --strict`，确认成功。
5. 提交该 Markdown 和所需图片，推送到 `main`。Actions 自动构建部署，无需修改文章导航。

详见 [新建文章与维护指南](docs/guides/writing.md)。注意：草稿只是不进入网站，公开仓库中的源文件仍公开；不要提交私人文件、密码或密钥。

## 目录

```text
.github/workflows/deploy.yml  # CI 检查与 GitHub Pages 部署
mkdocs.yml                   # 网站配置、固定页面导航
requirements.txt             # 固定依赖版本
requirements.in              # 直接依赖与主版本约束
templates/article.md         # 可复制模板，不参与网站构建
overrides/blog-post.html     # 显示明确日期和窄屏折叠目录
docs/
  index.md                   # 中文首页
  about.md                   # 关于
  topics.md                  # 四个内容方向
  tags.md                    # 自动标签索引
  guides/writing.md          # 写作与维护指南
  stylesheets/extra.css       # 少量阅读样式
  blog/
    index.md                 # 自动文章列表
    posts/
      ai-research/
      technology/
      learning/
      thinking/
```

## 配置和部署

在 `mkdocs.yml` 修改 `site_name`、`site_description` 和 `nav`。首页正文在 `docs/index.md`。文章的日期由元数据显式管理，不依赖 Git 的克隆时间。

GitHub Pages 的 Source 必须为 **GitHub Actions**。工作流对拉取请求执行严格构建，仅在 `main` 推送或手动触发时部署。部署任务使用自动提供的 `GITHUB_TOKEN` 与 OIDC，不需要添加个人 Token。公开仓库可使用免费的 GitHub Pages。

在仓库 **Actions → Build and deploy blog** 检查 `build` 和 `deploy`。失败时阅读对应日志，修复并推送；成功运行的部署页面会给出网站地址。

未来日期的文章要等日期到达并再次构建才会发布；没有设置定时任务。文章 URL 使用稳定的 `slug`，修改标题不会改变 URL。

## 依赖维护

直接依赖记录在 `requirements.in`，`requirements.txt` 固定构建环境。当前选择 MkDocs 1.x 和 Material 9.x；升级前在本地安装、严格构建并预览，验证后更新锁定文件。不添加评论、数据库、付费服务或额外前端框架。

## 内容与许可

建站文案和示例由 AI 辅助起草，作者可继续审阅修改。工程验证不等于研究事实核查。本站尚未授予统一的开放内容许可，第三方内容权利属于原作者。
