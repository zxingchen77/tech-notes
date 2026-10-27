#!/usr/bin/env python3
"""Watch a local Markdown inbox and publish only new articles. No extra dependencies."""
import argparse
from datetime import date, datetime
import fcntl
import hashlib
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid
from zoneinfo import ZoneInfo

import yaml

LOG = logging.getLogger('auto-publish')
CATEGORIES = {'AI 研究': 'ai-research', '技术实践': 'technology', '学习笔记': 'learning', '个人思考': 'thinking'}
EXCLUDED = {'readme.md', 'agents.md', 'skill.md', 'changelog.md', 'license.md'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temp.replace(path)


def load(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def command(repo, *args):
    result = subprocess.run(args, cwd=repo, text=True, capture_output=True, timeout=180,
                            env={**os.environ, 'GIT_TERMINAL_PROMPT': '0'})
    if result.returncode:
        # Do not copy arbitrary subprocess output (possibly article text) into logs.
        raise RuntimeError(f'{args[0]} {args[1]} 失败，退出码 {result.returncode}；请手动运行检查。')
    return result.stdout.strip()


def git(repo, *args):
    return command(repo, 'git', *args)


def parse(text):
    meta = {}
    if text.startswith('---\n'):
        match = re.match(r'\A---\n(.*?)\n---\s*\n', text, re.S)
        if not match:
            raise ValueError('YAML 元数据未闭合')
        meta = yaml.safe_load(match[1]) or {}
        if not isinstance(meta, dict):
            raise ValueError('YAML 元数据必须是键值形式')
        text = text[match.end():]
    return meta, text


def render(name, raw):
    text = raw.decode('utf-8-sig').replace('\r\n', '\n')
    meta, body = parse(text)
    if meta.get('draft') is True or meta.get('private') is True or meta.get('publish') is False:
        return None
    if re.search(r'(?i)(?:gh[pousr]_[\w]{20,}|github_pat_[\w]{20,}|sk-[\w-]{20,}|AKIA[A-Z0-9]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|(?:api[_-]?key|password|token|secret)\s*[:=]\s*[\"\x27]?[A-Za-z0-9_/-]{16,})', text):
        raise ValueError('检测到可能的凭据，请人工检查')
    if re.search(r'/Users/|/home/|file://|sandbox:|https?://[^\s/]+:[^\s/]+@', text):
        raise ValueError('含私人路径、带凭据网址或聊天下载链接，请先整理')
    # Relative assets are not silently omitted: author must resolve them first.
    for link in re.findall(r'\]\(\s*<?([^\s)>]+)', body):
        if not link.startswith(('https://', 'http://', '#', 'mailto:')):
            raise ValueError('包含相对图片/文件链接，请先把附件发布为可访问网址')
    heading = re.search(r'^#\s+(.+)$', body, re.M)
    title = str(meta.get('title') or (heading[1] if heading else Path(name).stem)).strip()
    if not title or len(title) > 300:
        raise ValueError('文章标题为空或过长')
    if heading:
        body = body[:heading.start()] + body[heading.end():]
    chosen = meta.get('categories') or []
    if isinstance(chosen, str):
        chosen = [chosen]
    if not isinstance(chosen, list) or any(c not in CATEGORIES for c in chosen):
        raise ValueError('categories 必须使用网站已有分类')
    if not chosen:
        if re.search(r'具身|机器人|人工智能|\bAI\b|大模型|ChatGPT|VLA', title, re.I):
            chosen = ['AI 研究']
        elif re.search(r'学习|阅读|笔记|知识管理', title):
            chosen = ['学习笔记']
        elif re.search(r'编程|工程|代码|技术|开发|数据库', title):
            chosen = ['技术实践']
        else:
            chosen = ['个人思考']
    tags = meta.get('tags', [])
    if not isinstance(tags, list) or any(not isinstance(t, str) for t in tags):
        raise ValueError('tags 必须为文字列表')
    today = datetime.now(ZoneInfo('Asia/Shanghai')).date()
    dates = meta.get('date', today)
    created = dates.get('created', today) if isinstance(dates, dict) else dates
    updated = dates.get('updated', created) if isinstance(dates, dict) else created
    created, updated = date.fromisoformat(str(created)[:10]), date.fromisoformat(str(updated)[:10])
    if created > today:
        return None
    slug = str(meta.get('slug') or f'article-{digest(name.encode())[:12]}')
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', slug):
        raise ValueError('slug 只能使用小写英文字母、数字与短横线')
    # Preserve export reference IDs as local numbered notes; never invent URLs.
    references = {}
    def cite(match):
        marker = match[0]
        number = references.setdefault(marker, len(references) + 1)
        return f'[^export-source-{number}]'
    body = re.sub(r'\ue200cite\ue202.*?\ue201', cite, body)
    if re.search(r'[\ue000-\uf8ff]', body):
        raise ValueError('还有无法识别的聊天导出标记，请人工整理')
    if '<!-- more -->' not in body:
        # Extract a preview, without rewriting or summarizing the research.
        preview = str(meta.get('description') or '')
        if not preview:
            for paragraph in re.split(r'\n\s*\n', body):
                paragraph = paragraph.strip()
                if not paragraph or paragraph.startswith(('#', '>', '|', '```', '!!!', '<', '[^')):
                    continue
                paragraph = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', paragraph)
                paragraph = re.sub(r'\[\^[^\]]+\]|[*_`]', '', paragraph)
                if len(paragraph) >= 50:
                    preview = paragraph[:180] + ('……' if len(paragraph) > 180 else '')
                    break
        preview = preview or f'本文围绕“{title}”展开，阅读全文了解分析与参考资料。'
        body = preview + '\n\n<!-- more -->\n\n' + body.lstrip()
    if references:
        notice = '\n\n!!! info "引用说明"\n    原稿的聊天引用已转为脚注，导出文件未提供对应网址，来源链接待作者补充。本次自动发布未进行事实核查。\n'
        body = body.replace('<!-- more -->', '<!-- more -->' + notice, 1)
        body += '\n\n' + '\n\n'.join(f'[^export-source-{n}]: 原稿引用 {n} 的原始网址未随文件提供，待作者补充。' for n in references.values()) + '\n'
    metadata = {'title': title, 'date': {'created': created, 'updated': updated}, 'slug': slug,
                'categories': chosen, 'tags': tags}
    output = '---\n' + yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False) + '---\n\n# ' + title + '\n\n' + body.lstrip()
    return f'docs/blog/posts/{CATEGORIES[chosen[0]]}/{slug}.md', output


class Publisher:
    def __init__(self, repo, source, state_dir, settle=120):
        self.repo, self.source, self.state_dir, self.settle = repo, source, state_dir, settle
        self.state_path = state_dir / 'state.json'
        self.journal = state_dir / 'pending.json'
        self.state = load(self.state_path, {'published': {}, 'observed': {}})

    def recover(self):
        pending = load(self.journal, None)
        if not pending:
            return
        # A committed transaction can safely retry its push after an outage or restart.
        head = git(self.repo, 'log', '-1', '--format=%s')
        if head != pending['message']:
            committed = git(self.repo, 'log', '--all', '-1', '--format=%H', '--fixed-strings', '--grep=' + pending['message'])
            if committed:
                raise RuntimeError('待恢复的发布提交之后出现其他提交，请人工检查 pending.json')
            for item in pending['items']:
                path = self.repo / item['target']
                if path.exists() and digest(path.read_bytes()) != item['output_hash']:
                    raise RuntimeError('中断的发布文件被修改，已停止自动恢复，请人工处理')
            for item in pending['items']:
                if git(self.repo, 'ls-files', '--', item['target']):
                    git(self.repo, 'restore', '--staged', '--', item['target'])
                (self.repo / item['target']).unlink(missing_ok=True)
            self.journal.unlink()
            return
        if git(self.repo, 'status', '--porcelain'):
            raise RuntimeError('推送恢复前发现工作区有修改，请先处理')
        git(self.repo, 'push', 'origin', 'main')
        for item in pending['items']:
            self.state['published'][item['name']] = {'sha256': item['source_hash'], 'target': item['target']}
            self.state['observed'].pop(item['name'], None)
            LOG.info('已推送文章：%s（网站上线结果请查看 GitHub Actions）', item['name'])
        save(self.state_path, self.state)
        self.journal.unlink()

    def scan(self, dry_run=False):
        if not dry_run:
            self.recover()
        items = []
        known_hashes = {p['sha256'] for p in self.state['published'].values()}
        # No recursion: the repository and unrelated subdirectories are never ingested.
        for path in sorted(self.source.iterdir()):
            if path.is_symlink() or not path.is_file() or path.suffix.lower() != '.md':
                continue
            if path.name.startswith(('.', '_', '~')) or path.name.lower() in EXCLUDED:
                continue
            if path.name in self.state['published']:
                continue
            try:
                if path.stat().st_size > 2_000_000:
                    raise ValueError('文件超过 2 MB，请人工发布')
                raw = path.read_bytes()
                sha = digest(raw)
                if sha in known_hashes:
                    continue
                old = self.state['observed'].get(path.name, {})
                if old.get('sha256') != sha:
                    old = {'sha256': sha, 'since': time.time()}
                    self.state['observed'][path.name] = old
                if not dry_run and time.time() - max(old['since'], path.stat().st_mtime) < self.settle:
                    continue
                article = render(path.name, raw)
                if article is None:
                    continue
                target, content = article
                if (self.repo / target).exists():
                    raise ValueError('目标文件已存在，不覆盖现有文章')
                slug = Path(target).stem
                for existing in (self.repo / 'docs/blog/posts').rglob('*.md'):
                    existing_meta, _ = parse(existing.read_text())
                    if str(existing_meta.get('slug', existing.stem)) == slug:
                        raise ValueError('文章网址 slug 与现有文章冲突')
                if any(Path(i['target']).stem == slug for i in items):
                    raise ValueError('同批新文章使用了重复 slug')
                items.append({'name': path.name, 'source_hash': sha, 'target': target,
                              'content': content, 'output_hash': digest(content.encode())})
                known_hashes.add(sha)
            except (ValueError, UnicodeError, yaml.YAMLError) as error:
                LOG.warning('跳过 %s：%s', path.name, type(error).__name__ + ': ' + str(error) if not isinstance(error, yaml.YAMLError) else 'YAML 格式错误')
        if dry_run:
            for item in items:
                print(f'{item["name"]} -> {item["target"]}')
            print(f'待发布 {len(items)} 篇（预览未写文件、未提交或推送）。')
            return
        save(self.state_path, self.state)
        if not items:
            return
        if git(self.repo, 'branch', '--show-current') != 'main':
            raise RuntimeError('当前分支不是 main，暂停发布')
        if git(self.repo, 'status', '--porcelain'):
            raise RuntimeError('工作区有未提交改动，暂停自动发布以避免混入其他文件')
        git(self.repo, 'fetch', 'origin', 'main')
        if git(self.repo, 'rev-parse', 'HEAD') != git(self.repo, 'rev-parse', 'origin/main'):
            raise RuntimeError('本地与远程 main 不一致，请先人工同步')
        transaction = {'message': f'auto-publish: {len(items)} new article(s) [{uuid.uuid4().hex[:12]}]',
                       'items': [{k: v for k, v in item.items() if k != 'content'} for item in items]}
        save(self.journal, transaction)
        for item in items:
            target = self.repo / item['target']
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(item['content'])
        try:
            command(self.repo, sys.executable, '-m', 'mkdocs', 'build', '--strict')
        except Exception:
            self.recover()  # Removes only the unchanged files owned by this transaction.
            raise
        targets = [item['target'] for item in items]
        git(self.repo, 'add', '--', *targets)
        git(self.repo, 'commit', '-m', transaction['message'], '--', *targets)
        self.recover()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--source', type=Path)
    parser.add_argument('--state-dir', type=Path)
    parser.add_argument('--watch', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--settle-seconds', type=int, default=120)
    args = parser.parse_args()
    repo = args.repo.resolve()
    source = (args.source or repo.parent).resolve()
    state_dir = (args.state_dir or repo / '.autopublish').resolve()
    state_dir.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(state_dir / 'watcher.log', maxBytes=1_000_000, backupCount=3, encoding='utf-8')
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s', handlers=[handler, logging.StreamHandler()])
    if args.dry_run:
        Publisher(repo, source, state_dir, args.settle_seconds).scan(dry_run=True)
        return
    with (state_dir / 'lock').open('w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            LOG.info('监听程序已运行；请查看 .autopublish/watcher.log。')
            return
        publisher = Publisher(repo, source, state_dir, args.settle_seconds)
        LOG.info('开始扫描：%s；等待文件稳定 %s 秒', source, args.settle_seconds)
        while True:
            try:
                publisher.scan(args.dry_run)
            except Exception as error:
                LOG.error('%s', error)
                if not args.watch:
                    raise SystemExit(1)
            if not args.watch or args.dry_run:
                break
            time.sleep(30)


if __name__ == '__main__':
    main()
