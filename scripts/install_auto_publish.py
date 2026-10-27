#!/usr/bin/env python3
"""Install/uninstall the macOS login watcher for this checkout."""
import argparse
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys

from auto_publish import Publisher, digest, parse, save

LABEL = 'com.zxingchen77.tech-notes-auto-publish'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--uninstall', action='store_true')
    args = parser.parse_args()
    if sys.platform != 'darwin':
        parser.error('此安装脚本仅适用于 macOS；其他系统可直接运行 auto_publish.py --watch')
    repo = Path(__file__).resolve().parents[1]
    plist = Path.home() / 'Library/LaunchAgents' / (LABEL + '.plist')
    service = f'gui/{os.getuid()}/{LABEL}'
    subprocess.run(['launchctl', 'bootout', service], capture_output=True)
    if args.uninstall:
        plist.unlink(missing_ok=True)
        print('已停止自动发布；原文章和发布记录保留。')
        return
    state_dir = repo / '.autopublish'
    state_dir.mkdir(exist_ok=True)
    publisher = Publisher(repo, repo.parent, state_dir)
    # Seed only documents whose titles already match published posts.
    existing = {}
    for path in (repo / 'docs/blog/posts').rglob('*.md'):
        meta, body = parse(path.read_text())
        title = meta.get('title')
        if title:
            existing[''.join(str(title).split())] = str(path.relative_to(repo))
    for source in repo.parent.glob('*.md'):
        if source.is_symlink() or source.name in publisher.state['published']:
            continue
        raw = source.read_bytes()
        meta, body = parse(raw.decode('utf-8-sig'))
        headings = [line[2:].strip() for line in body.splitlines() if line.startswith('# ')]
        title = meta.get('title') or (headings[0] if headings else source.stem)
        target = existing.get(''.join(str(title).split()))
        if target:
            publisher.state['published'][source.name] = {'sha256': digest(raw), 'target': target}
            print('登记已发布：', source.name)
    save(publisher.state_path, publisher.state)
    logs = Path.home() / 'Library/Logs/tech-notes-auto-publish'
    logs.mkdir(parents=True, exist_ok=True)
    executable_paths = {str(Path(shutil.which(name)).parent) for name in ('git', 'gh') if shutil.which(name)}
    plist.parent.mkdir(parents=True, exist_ok=True)
    config = {
        'Label': LABEL,
        'ProgramArguments': [str(repo / '.venv/bin/python'), str(repo / 'scripts/auto_publish.py'), '--watch'],
        'WorkingDirectory': str(repo),
        'RunAtLoad': True,
        'KeepAlive': True,
        'ThrottleInterval': 30,
        'ProcessType': 'Background',
        'EnvironmentVariables': {'PATH': ':'.join(sorted(executable_paths)) + ':/usr/bin:/bin:/usr/sbin:/sbin', 'PYTHONUNBUFFERED': '1'},
        'StandardOutPath': str(logs / 'stdout.log'),
        'StandardErrorPath': str(logs / 'stderr.log'),
    }
    plist.write_bytes(plistlib.dumps(config))
    subprocess.run(['launchctl', 'bootstrap', f'gui/{os.getuid()}', str(plist)], check=True)
    print('已安装登录监听：', LABEL)
    print('日志：', state_dir / 'watcher.log')


if __name__ == '__main__':
    main()
