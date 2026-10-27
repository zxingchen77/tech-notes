import importlib.util
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('publisher', Path(__file__).parents[1] / 'scripts/auto_publish.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class RenderingTests(unittest.TestCase):
    def test_drafts_and_private_never_render(self):
        for flag in ('draft: true', 'private: true', 'publish: false'):
            self.assertIsNone(module.render('test.md', f'---\n{flag}\n---\n# Test\n正文'.encode()))

    def test_paths_credentials_and_local_assets_are_blocked(self):
        for body in ('/Users/example/private', 'sandbox:/mnt/data/a.docx', '![图](image.png)', 'ghp_' + 'x' * 30):
            with self.assertRaises(ValueError):
                module.render('test.md', ('# Test\n' + body).encode())

    def test_body_and_reference_notes(self):
        body = '# AI 研究\n\n## 结论\n\n正文。citeturn1search1\n\n```python\nprint(1)\n```'
        path, result = module.render('test.md', body.encode())
        self.assertIn('/ai-research/', path)
        self.assertIn('print(1)', result)
        self.assertIn('正文。[^export-source-1]', result)
        self.assertNotIn('', result)
        self.assertIn('<!-- more -->', result)

    def test_frontmatter_controls_slug(self):
        path, result = module.render('test.md', b'---\nslug: custom-name\ncategories: ["\xe6\x8a\x80\xe6\x9c\xaf\xe5\xae\x9e\xe8\xb7\xb5"]\n---\n# Test\nBody')
        self.assertEqual(path, 'docs/blog/posts/technology/custom-name.md')
        self.assertEqual(result.count('# Test'), 1)


class GitIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        self.inbox = self.root / 'inbox'
        self.inbox.mkdir()
        self.remote = self.root / 'remote.git'
        subprocess.run(['git', 'init', '--bare', str(self.remote)], check=True, capture_output=True)
        self.git('init', '-b', 'main')
        self.git('config', 'user.name', 'Test')
        self.git('config', 'user.email', 'test@example.invalid')
        (self.repo / '.gitignore').write_text('site/\n')
        (self.repo / 'mkdocs.yml').write_text('site_name: Test\ntheme:\n  name: material\nplugins:\n  - blog\nmarkdown_extensions:\n  - footnotes\n')
        (self.repo / 'docs/blog/posts').mkdir(parents=True)
        (self.repo / 'docs/index.md').write_text('# Test\n')
        (self.repo / 'docs/blog/index.md').write_text('# Blog\n')
        self.git('add', '.')
        self.git('commit', '-m', 'init')
        self.git('remote', 'add', 'origin', str(self.remote))
        self.git('push', '-u', 'origin', 'main')
        self.state_dir = self.root / 'state'
        self.state_dir.mkdir()
        self.publisher = module.Publisher(self.repo, self.inbox, self.state_dir, settle=0)
        self.article = self.inbox / 'new.md'
        self.article.write_text('# AI 测试文章\n\n这里只是本地隔离测试。\n')

    def tearDown(self):
        self.temp.cleanup()

    def git(self, *args):
        return module.git(self.repo, *args)

    def test_publish_build_push_and_no_duplicates(self):
        self.publisher.scan()
        first = self.git('rev-parse', 'HEAD')
        self.assertEqual(first, self.git('rev-parse', 'origin/main'))
        self.assertTrue((self.repo / 'site/blog').exists())
        self.assertIn('new.md', self.publisher.state['published'])
        # Editing or renaming a published source must not duplicate/overwrite it.
        original = self.article.read_bytes()
        self.article.write_text('# Updated\n')
        (self.inbox / 'renamed.md').write_bytes(original)
        self.publisher.scan()
        self.assertEqual(first, self.git('rev-parse', 'HEAD'))

    def test_dirty_tree_stops_publication(self):
        (self.repo / 'unrelated.txt').write_text('private unrelated work')
        with self.assertRaises(RuntimeError):
            self.publisher.scan()
        self.assertFalse(list((self.repo / 'docs/blog/posts').rglob('*.md')))
        self.assertEqual('private unrelated work', (self.repo / 'unrelated.txt').read_text())

    def test_settle_and_dry_run(self):
        self.publisher.settle = 120
        self.publisher.scan()
        self.assertFalse(self.publisher.state['published'])
        self.publisher.scan(dry_run=True)
        self.assertFalse(list((self.repo / 'docs/blog/posts').rglob('*.md')))

    def test_failed_build_removes_only_generated_files(self):
        original = module.command
        def fail_build(repo, *args):
            if 'mkdocs' in args:
                raise RuntimeError('simulated build failure')
            return original(repo, *args)
        with patch.object(module, 'command', side_effect=fail_build):
            with self.assertRaises(RuntimeError):
                self.publisher.scan()
        self.assertEqual('', self.git('status', '--porcelain'))
        self.assertFalse(self.publisher.journal.exists())

    def test_push_failure_recovers_after_restart(self):
        original = module.git
        def fail_push(repo, *args):
            if args[0] == 'push':
                raise RuntimeError('simulated network outage')
            return original(repo, *args)
        with patch.object(module, 'git', side_effect=fail_push):
            with self.assertRaises(RuntimeError):
                self.publisher.scan()
        commit = self.git('rev-parse', 'HEAD')
        self.assertTrue(self.publisher.journal.exists())
        restarted = module.Publisher(self.repo, self.inbox, self.state_dir, settle=0)
        restarted.scan()
        self.assertEqual(commit, self.git('rev-parse', 'origin/main'))
        self.assertEqual(commit, self.git('rev-parse', 'HEAD'))
        self.assertIn('new.md', restarted.state['published'])
        self.assertFalse(restarted.journal.exists())


if __name__ == '__main__':
    unittest.main()
