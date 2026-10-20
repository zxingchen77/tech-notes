# 新建文章与日常维护

## 准备环境与本地预览

首次需要 Git 与 Python 3.12：

```bash
git clone https://github.com/zxingchen77/tech-notes.git
cd tech-notes
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m mkdocs serve
```

打开终端显示的本地地址，保存文章后页面自动刷新。Windows PowerShell 使用 `.venv\Scripts\Activate.ps1` 激活环境。已有项目时直接进入目录并激活环境即可。

## 复制模板

复制仓库中的 [Markdown 文章模板](https://github.com/zxingchen77/tech-notes/blob/main/templates/article.md)：

```bash
cp templates/article.md docs/blog/posts/ai-research/my-first-research.md
```

| 存放目录（相对项目根目录） | `categories` 分类 |
| --- | --- |
| `docs/blog/posts/ai-research/` | `AI 研究` |
| `docs/blog/posts/technology/` | `技术实践` |
| `docs/blog/posts/learning/` | `学习笔记` |
| `docs/blog/posts/thinking/` | `个人思考` |

目录整理源文件，网站分类由 `categories` 决定。每篇文章可有多个分类和标签，无需逐篇修改导航，列表、分类、标签与年份归档会自动生成。

## 完成正文

1. 修改 `title` 和正文一级标题，保持一致。
2. 填写实际 `date.created` 与 `date.updated`，格式 `YYYY-MM-DD`。
3. 填写唯一的英文 `slug`，发布后保持稳定，避免旧链接失效。
4. 标题后写 100～200 字摘要，保留后面的 `<!-- more -->` 分隔符。
5. 完成核心结论、正文分析、实践建议（适用时）、参考资料、更新记录。
6. 标明 AI 参与、人工核查范围和待验证事项，不把 AI 输出本身当作事实来源。

图片放在 `docs/assets/images/`，使用相对路径引用并随文章提交。

模板默认 `draft: true`，正式构建不会发布草稿，本地预览可以查看。**公开仓库里的草稿源文件仍公开**，私人内容必须保留在仓库外。未来日期文章会被构建过滤；日期到达后需要推送或手动运行 Actions，本项目没有定时发布任务。

## 检查与发布

将 `draft` 改为 `false` 或删除该字段，然后运行：

```bash
python -m mkdocs build --strict
git add docs/blog/posts/ai-research/my-first-research.md
git commit -m "docs: publish first research article"
git push origin main
```

构建成功后再提交；检查目录、代码、链接和窄屏排版。严格构建不等于外部资料已经核实。有图片时把对应图片一起提交。也可以在 GitHub 网页进入对应目录，通过 **Add file → Create new file** 添加 Markdown 并提交到 `main`。

## 查看部署结果

打开 [GitHub Actions](https://github.com/zxingchen77/tech-notes/actions)，选择 **Build and deploy blog**，确认最新提交的 `build` 和 `deploy` 均为绿色。失败时打开红色步骤阅读日志，修复后推送；也可以使用 **Run workflow** 手动触发。

成功后访问 [博客](https://zxingchen77.github.io/tech-notes/)。缓存可能短暂延迟，刷新并核对运行对应的提交。迁移到新仓库时，在 **Settings → Pages → Build and deployment → Source** 选择 **GitHub Actions**，并同步修改站点 URL 和仓库入口。

## 修改名称、介绍和导航

编辑 `mkdocs.yml`：

| 配置 | 用途 |
| --- | --- |
| `site_name` | 网站名称 |
| `site_description` | 网站介绍 |
| `site_url` | 公开地址 |
| `repo_url`、`repo_name` | GitHub 仓库入口 |
| `nav` | 固定页面导航，无需列出单篇文章 |
| `plugins.blog.categories_allowed` | 允许的分类 |
| `theme.palette` | 明暗配色 |

首页正文在 `docs/index.md`，关于页面在 `docs/about.md`，样式在 `docs/stylesheets/extra.css`。添加分类后同步更新分类说明与本指南。

## 维护依赖

直接依赖在 `requirements.in`，构建版本固定在 `requirements.txt`。升级时先在本地安装拟升级版本，严格构建并预览通过后再更新版本文件；不要直接引入未经验证的新主版本。
