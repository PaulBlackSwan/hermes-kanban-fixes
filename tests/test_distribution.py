"""Offline acceptance tests. Fixtures are disposable exact-base Git checkouts.

Set KANBAN_TEST_REPOSITORY to a local repository containing the qualified commit.
No production imports, database access or network access.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BASE = 'bf0203a794a07aac3ff764972ab9087baa4e4f4e'


def run(*args, **kw):
    return subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, **kw)


class Distribution(unittest.TestCase):
    def setUp(self):
        origin = os.environ.get('KANBAN_TEST_REPOSITORY')
        if not origin:
            self.skipTest('set KANBAN_TEST_REPOSITORY to a local exact-base repository')
        scratch = Path(os.environ.get('TMPDIR', Path.home() / '.cache'))
        scratch.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(prefix='kanban-package-test-', dir=scratch)
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.source = self.home / 'checkout'
        # A standalone clone, never a linked worktree in the source repository.
        p = run('git', 'clone', '--shared', '--no-checkout', '--quiet', origin, str(self.source))
        self.assertEqual(p.returncode, 0, p.stdout)
        p = run('git', '-C', str(self.source), 'checkout', '--detach', '--quiet', BASE)
        self.assertEqual(p.returncode, 0, p.stdout)
        self.env = dict(os.environ, HOME=str(self.home), PYTHONDONTWRITEBYTECODE='1', GIT_CONFIG_GLOBAL='/dev/null')
        self.manifest = json.loads((ROOT / 'manifest.json').read_text())
        self.first = next(p for p, x in self.manifest['files'].items() if x['before_sha256'])

    def cli(self, *args, root=ROOT):
        return run(sys.executable, '-B', str(root / 'tools/install.py'), '--source', str(self.source), *args, env=self.env)

    def ok(self, *args):
        p = self.cli(*args)
        self.assertEqual(p.returncode, 0, p.stdout)
        return p.stdout

    def refused(self, *args, root=ROOT):
        p = self.cli(*args, root=root)
        self.assertNotEqual(p.returncode, 0, p.stdout)
        self.assertIn('REFUSED', p.stdout)

    def snapshot(self):
        return {str(p.relative_to(self.source)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in self.source.rglob('*') if p.is_file() and '.git' not in p.relative_to(self.source).parts}

    def test_dry_run_writes_nothing(self):
        before = self.snapshot()
        self.assertIn('dry-run', self.ok())
        self.assertEqual(self.snapshot(), before)
        self.assertFalse((self.source / '.hermes-kanban-fixes').exists())

    def test_apply_idempotence_and_rollback(self):
        before = self.snapshot()
        unrelated = self.source / 'unrelated.txt'
        unrelated.write_text('preserve me')
        self.assertIn('applied', self.ok('--apply'))
        for name, item in self.manifest['files'].items():
            self.assertEqual(hashlib.sha256((self.source / name).read_bytes()).hexdigest(), item['after_sha256'])
        snap = self.snapshot()
        self.assertIn('already_applied', self.ok('--apply'))
        self.assertEqual(snap, self.snapshot())
        self.assertIn('dry-run', self.ok('--rollback'))
        self.assertEqual(snap, self.snapshot())
        self.assertIn('rolled_back', self.ok('--rollback', '--apply'))
        self.assertEqual(unrelated.read_text(), 'preserve me')
        for name, item in self.manifest['files'].items():
            p = self.source / name
            if item['before_sha256'] is None:
                self.assertFalse(p.exists())
            else:
                self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(), before[name])

    def test_modified_refused_without_writes(self):
        (self.source / self.first).write_text('modified')
        before = self.snapshot()
        self.refused('--apply')
        self.assertEqual(before, self.snapshot())

    def test_missing_file_refused(self):
        (self.source / self.first).unlink()
        self.refused('--apply')

    def test_symlink_refused(self):
        target = self.source / self.first
        outside = self.home / 'outside'
        outside.write_bytes(target.read_bytes())
        target.unlink()
        target.symlink_to(outside)
        self.refused('--apply')
        self.assertEqual(outside.read_bytes(), run('git', '-C', str(self.source), 'show', BASE + ':' + self.first).stdout.encode())

    def test_traversal_refused(self):
        p = run(sys.executable, '-B', str(ROOT / 'tools/install.py'), '--source', str(self.source / '..' / 'checkout'), '--apply', env=self.env)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn('REFUSED', p.stdout)

    def test_manifest_tamper_refused(self):
        release = self.home / 'release'
        shutil.copytree(ROOT, release, ignore=shutil.ignore_patterns('.git', 'dist', 'verification', '__pycache__'))
        manifest = release / 'manifest.json'
        manifest.write_text(manifest.read_text() + ' ')
        self.refused('--apply', root=release)

    def test_partial_state_refused(self):
        self.ok('--apply')
        original = subprocess.check_output(['git', '-C', str(self.source), 'show', BASE + ':' + self.first])
        (self.source / self.first).write_bytes(original)
        before = self.snapshot()
        self.refused('--apply')
        self.refused('--rollback', '--apply')
        self.assertEqual(before, self.snapshot())

    def test_rollback_modified_refused(self):
        self.ok('--apply')
        (self.source / self.first).write_text('concurrent change')
        before = self.snapshot()
        self.refused('--rollback', '--apply')
        self.assertEqual(before, self.snapshot())

    def test_archive_reproducible_and_extracted_install(self):
        import zipfile
        archives = [self.home / 'one.zip', self.home / 'two.zip']
        for archive in archives:
            p = run(sys.executable, '-B', str(ROOT / 'tools/package_release.py'), '--output', str(archive), env=self.env)
            self.assertEqual(p.returncode, 0, p.stdout)
        self.assertEqual(archives[0].read_bytes(), archives[1].read_bytes())
        release = self.home / 'extracted'
        with zipfile.ZipFile(archives[0]) as z:
            names = z.namelist()
            self.assertEqual(len(names), len(set(names)))
            self.assertFalse(any(any(x in n for x in ('.git/', 'verification/', '__pycache__/', 'voice', '.venv/', 'node_modules/')) for n in names))
            sums = z.read('SHA256SUMS').decode().splitlines()
            self.assertEqual(len(sums), len(names) - 1)
            for line in sums:
                digest, name = line.split('  ', 1)
                self.assertEqual(hashlib.sha256(z.read(name)).hexdigest(), digest)
            z.extractall(release)
        p = self.cli(root=release)
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertIn('dry-run', p.stdout)
        p = self.cli('--apply', root=release)
        self.assertEqual(p.returncode, 0, p.stdout)
        p = self.cli('--rollback', '--apply', root=release)
        self.assertEqual(p.returncode, 0, p.stdout)

    def test_backup_tamper_refused(self):
        self.ok('--apply')
        backup = self.source / '.hermes-kanban-fixes' / '0.1.0-rc.1' / 'before' / self.first
        backup.write_text('tampered backup')
        before = self.snapshot()
        self.refused('--rollback', '--apply')
        self.assertEqual(before, self.snapshot())

    def test_patch_tamper_refused(self):
        release = self.home / 'release'
        shutil.copytree(ROOT, release, ignore=shutil.ignore_patterns('.git', 'dist', 'verification', '__pycache__'))
        patch = release / 'patches/kanban-fixes.patch'
        patch.write_bytes(patch.read_bytes() + b'\n')
        self.refused('--apply', root=release)

    def test_parent_symlink_refused(self):
        original = self.source / 'gateway'
        outside = self.home / 'gateway'
        original.rename(outside)
        original.symlink_to(outside, target_is_directory=True)
        self.refused('--apply')

    def test_unknown_checkout_refused(self):
        p = run('git', '-C', str(self.source), 'checkout', '--detach', '--quiet', BASE + '^')
        self.assertEqual(p.returncode, 0, p.stdout)
        self.refused('--apply')


if __name__ == '__main__':
    unittest.main()
