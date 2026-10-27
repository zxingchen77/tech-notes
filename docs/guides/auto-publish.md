# 文件夹自动发布

## 平时怎么用

1. 在 `tech-notes` 仓库的上一级文件夹里保存一篇新的 `.md` 文章，使用 UTF-8 编码。
2. 保存后保持文件不变至少两分钟。后台程序每 30 秒检查一次，只扫描这一层文件，不扫描子文件夹。
3. 程序自动生成博客文章、运行严格构建，然后提交推送；GitHub Actions 随后部署，通常还需要几分钟。
4. 到网站的 **文章** 页面查看新文章，或在 [GitHub Actions](https://github.com/zxingchen77/tech-notes/actions) 查看部署结果。

电脑需要开机、登录并联网。休眠或关机期间暂停，恢复运行后补扫。安装时会按标题登记已发布文章，避免重复导入。首页的精选链接手动维护；自动文章列表、分类、标签和搜索会随部署更新。

**这个文件夹是公开发布入口。** 不准备发布的文件请以 `_` 开头命名，例如 `_还没写完.md`，或者在文件最前面添加：

```yaml
---
draft: true
---
```

`private: true` 或 `publish: false` 也会阻止导入。隐藏文件、符号链接、README、AGENTS、SKILL 等说明文件不会导入。程序会拦截部分常见凭据和本地路径，但不等于完整的隐私审查。

## 可以直接放普通 Markdown

程序使用第一个一级标题作为文章标题，没有标题时使用文件名。默认使用发布当天日期，按标题关键词选择已有分类，生成稳定的文章网址，并从正文摘取列表摘要，正文不会交给 AI 改写。

需要自己指定信息时，在文件开头添加：

```yaml
---
title: 你的文章标题
date:
  created: 2026-10-27
  updated: 2026-10-27
slug: your-unique-article-name
categories:
  - AI 研究
tags:
  - 机器人
description: 用一段话介绍本文的研究问题和核心结论。
draft: false
---
```

分类可选 `AI 研究`、`技术实践`、`学习笔记`、`个人思考`。`slug` 只能用小写英文字母、数字和短横线，并且不能与已有文章重复。未来日期的文章会等待日期到达后再导入。

相对路径附件、电脑私人路径和聊天下载链接会阻止发布，请先换成可公开访问的网址。聊天导出的特殊引用标记会转为脚注，并说明原始网址缺失，需作者补充；自动发布不代表完成事实核查。完整文章模板见 [写作与维护](writing.md)。

## 修改或删除旧文章

目前只自动导入新文件。**修改已经发布的源文件不会自动更新博客**，删除源文件也不会删除博客文章。要更新旧文，请修改仓库内对应的 `docs/blog/posts/` 文件并提交推送，或让助手帮你更新。相同内容改名不会重复发布。

发布记录保存在本机 `.autopublish/state.json`，不要随意删除。该目录不上传 GitHub。

## 安装与停止

在仓库目录打开终端，先按照 README 准备 `.venv` 并安装依赖，再确认 `gh auth status` 正常、仓库位于 `main` 且已同步远程。

安装（或重新安装）登录后台监听：

```bash
.venv/bin/python scripts/install_auto_publish.py
```

停止并取消登录启动：

```bash
.venv/bin/python scripts/install_auto_publish.py --uninstall
```

预览待发布文章，不提交或推送：

```bash
.venv/bin/python scripts/auto_publish.py --dry-run
```

如果移动了文件夹或重新创建了虚拟环境，请重新安装监听。监听依赖 macOS 的 launchd；它不需要打开 Codex 窗口。

## 没有发布时怎么查

日志位于仓库的 `.autopublish/watcher.log`；启动错误也会写到 `~/Library/Logs/tech-notes-auto-publish/stderr.log`。

```bash
tail -n 30 .autopublish/watcher.log
```

- **文件还在写、是草稿或未来日期**：等待或修正元数据。
- **格式、链接或凭据提示**：按日志整理原文，保存后会重新尝试。
- **工作区有未提交修改**：先完成自己的修改并提交推送，自动程序不会混入其他文件。
- **本地与远程不同步**：先手动同步 `main`，自动程序不会强制覆盖远程。
- **构建失败**：使用预览检查候选文章，并运行 `.venv/bin/python -m mkdocs build --strict` 检查现有站点；自动生成的失败文件会回退，原稿保留。
- **推送失败**：检查网络和 `gh auth status`。已提交的发布任务会重试推送，重启后也能继续。
- **已推送但网页未更新**：查看 Actions 的 `build`、`deploy` 结果。脚本的“已推送”不等于线上部署已经完成。

遇到中断事务或人工修改冲突时，先保留 `.autopublish/pending.json` 和日志，让助手排查，不要手动删除发布记录。
