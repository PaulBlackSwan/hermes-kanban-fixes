#!/usr/bin/env python3
"""Explicit offline source patch installer. Dry-run by default; stdlib + Git.

No Hermes imports, profile discovery, settings, database access or restart.
Use a trusted package, a quiescent checkout and one installer at a time.
Hashes detect corruption, not publisher impersonation.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

BASE = 'bf0203a794a07aac3ff764972ab9087baa4e4f4e'
VERSION = '0.1.0-rc.2'
MANIFEST_SHA256 = '79314a8e6a0bdf1567e5f1ef4d998a7470cbd9b6f71d366d58011acbbc49d384'
NAMES = (
    'gateway/kanban_watchers_notifier.py',
    'gateway/session_local.py',
    'tests/gateway/test_local_kanban_wake.py',
    'hermes_cli/kanban_db.py',
    'tui_gateway/session_notifications.py',
    'scripts/kanban_block_followup.py',
    'tests/gateway/test_kanban_block_followup_wake.py',
    'tests/hermes_cli/test_kanban_block_followup.py',
    'tests/tui_gateway/test_kanban_block_followup_notifications.py',
)
ROOT = Path(__file__).absolute().parents[1]
STATE = '.hermes-kanban-fixes'


class Refusal(ValueError):
    pass


def sha(data):
    return hashlib.sha256(data).hexdigest()


def safe(path):
    """Reject traversal, symlink ancestors and nonregular/hardlinked files."""
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts:
        raise Refusal('absolute path without traversal required')
    for p in reversed((path, *path.parents)):
        try:
            s = p.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(s.st_mode):
            raise Refusal('symlink refused: ' + str(p))
        if not stat.S_ISDIR(s.st_mode) and not (stat.S_ISREG(s.st_mode) and s.st_nlink == 1):
            raise Refusal('nonregular or hardlinked file refused: ' + str(p))
    return path


def read(path):
    p = safe(path)
    if not p.is_file():
        raise Refusal('required file missing: ' + str(p))
    if p.stat().st_size > 16 * 1024 * 1024:
        raise Refusal('file exceeds size limit')
    return p.read_bytes()


def digest(path):
    p = safe(path)
    return sha(read(p)) if p.exists() else None


def git(source, *args, data=None):
    env = dict(os.environ, GIT_OPTIONAL_LOCKS='0', GIT_CONFIG_GLOBAL=os.devnull,
               GIT_CONFIG_NOSYSTEM='1')
    # Do not allow ambient Git repository/index overrides to redirect operations.
    for key in list(env):
        if key.startswith('GIT_') and key not in {'GIT_OPTIONAL_LOCKS', 'GIT_CONFIG_GLOBAL', 'GIT_CONFIG_NOSYSTEM'}:
            del env[key]
    result = subprocess.run(['git', '-C', str(source), *args], input=data,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    if result.returncode:
        raise Refusal('Git check failed: ' + result.stderr.decode(errors='replace').strip())
    return result.stdout


def package():
    data = read(ROOT / 'manifest.json')
    if sha(data) != MANIFEST_SHA256:
        raise Refusal('manifest integrity mismatch')
    m = json.loads(data)
    if m['base_commit'] != BASE or m['version'] != VERSION or set(m['files']) != set(NAMES):
        raise Refusal('unsupported manifest')
    patch = read(ROOT / 'patches/kanban-fixes.patch')
    if sha(patch) != m['patch_sha256']:
        raise Refusal('patch integrity mismatch')
    return m, patch


def identity(source):
    safe(source)
    if not source.is_dir():
        raise Refusal('source checkout missing')
    if git(source, 'rev-parse', '--show-toplevel').decode().strip() != str(source):
        raise Refusal('--source must name the checkout root exactly')
    if git(source, 'rev-parse', 'HEAD').decode().strip() != BASE:
        raise Refusal('unsupported HEAD; only exact qualified base accepted')


def hashes(source):
    return {n: digest(source / n) for n in NAMES}


def expected(m, side):
    return {n: m['files'][n][side + '_sha256'] for n in NAMES}


def backup_path(folder, name):
    # Fixed identifiers only: no backup path ever comes from the ledger.
    return folder / 'before' / name


def load_ledger(source, folder, m):
    ledger = json.loads(read(folder / 'ledger.json'))
    if (set(ledger) != {'version', 'source', 'manifest_sha256', 'files'}
            or ledger['version'] != VERSION or ledger['source'] != str(source)
            or ledger['manifest_sha256'] != MANIFEST_SHA256
            or set(ledger['files']) != set(NAMES)):
        raise Refusal('invalid backup ledger identity')
    for n in NAMES:
        item = ledger['files'][n]
        before = m['files'][n]['before_sha256']
        if set(item) != {'before_sha256', 'mode'} or item['before_sha256'] != before:
            raise Refusal('invalid backup ledger entry')
        if type(item['mode']) is not int or not 0 <= item['mode'] <= 0o777:
            raise Refusal('invalid backup mode')
        if digest(backup_path(folder, n)) != before:
            raise Refusal('backup integrity mismatch: ' + n)
    return ledger


def restore(source, folder, ledger):
    for n in NAMES:
        target = safe(source / n)
        item = ledger['files'][n]
        if item['before_sha256'] is None:
            target.unlink()
        else:
            target.write_bytes(read(backup_path(folder, n)))
            target.chmod(item['mode'])


def execute(source, apply=False, rollback=False):
    m, patch = package()
    identity(source)
    before, after = expected(m, 'before'), expected(m, 'after')
    current = hashes(source)
    folder = safe(source / STATE / VERSION)
    if rollback:
        ledger = load_ledger(source, folder, m)
        if current != after:
            raise Refusal('rollback requires every target to match the installed after hash; preserve edits first')
        if not apply:
            return {'status': 'dry-run', 'operation': 'rollback', 'files': list(NAMES)}
    else:
        if current == after:
            return {'status': 'already_applied', 'files': list(NAMES)}
        if current != before:
            raise Refusal('modified, missing or partial target state; no writes; reconcile manually')
        if folder.exists():
            raise Refusal('backup ledger already exists; preserve and reconcile before reapplying')
        git(source, 'apply', '--check', '--whitespace=nowarn', '-', data=patch)
        if not apply:
            return {'status': 'dry-run', 'operation': 'apply', 'files': list(NAMES)}
    state = safe(source / STATE)
    state.mkdir(mode=0o700, exist_ok=True)
    lock = safe(state / 'install.lock')
    try:
        handle = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    except FileExistsError:
        raise Refusal('installer lock exists; verify no writer before manual recovery') from None
    os.close(handle)
    try:
        # Detect an intervening writer before the first target write.
        identity(source)
        if hashes(source) != current:
            raise Refusal('targets changed during preflight')
        if rollback:
            ledger = load_ledger(source, folder, m)
            restore(source, folder, ledger)
            if hashes(source) != before:
                raise Refusal('rollback verification failed; backups retained')
            return {'status': 'rolled_back', 'backups_retained': True}
        folder.mkdir(mode=0o700)
        ledger = {'version': VERSION, 'source': str(source),
                  'manifest_sha256': MANIFEST_SHA256, 'files': {}}
        for n in NAMES:
            target = safe(source / n)
            mode = stat.S_IMODE(target.stat().st_mode) & 0o777 if target.exists() else 0o644
            ledger['files'][n] = {'before_sha256': before[n], 'mode': mode}
            if before[n] is not None:
                dest = backup_path(folder, n)
                dest.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                with dest.open('xb') as f:
                    f.write(read(target))
                dest.chmod(0o600)
        with (folder / 'ledger.json').open('x') as f:
            json.dump(ledger, f, sort_keys=True, indent=2)
            f.write('\n')
        (folder / 'ledger.json').chmod(0o600)
        load_ledger(source, folder, m)
        git(source, 'apply', '--whitespace=nowarn', '-', data=patch)
        if hashes(source) != after:
            raise Refusal('post-apply hash mismatch; backups retained; stop and reconcile manually')
        git(source, 'apply', '--reverse', '--check', '--whitespace=nowarn', '-', data=patch)
        return {'status': 'applied', 'backup': str(folder), 'restart_performed': False}
    finally:
        lock.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, help='explicit absolute Git checkout root')
    parser.add_argument('--apply', action='store_true', help='authorize writes (otherwise dry-run)')
    parser.add_argument('--rollback', action='store_true', help='restore targeted backups; still dry-run unless --apply')
    args = parser.parse_args()
    try:
        result = execute(Path(args.source), args.apply, args.rollback)
    except (Refusal, OSError, ValueError, KeyError) as e:
        print('REFUSED: ' + str(e), file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
