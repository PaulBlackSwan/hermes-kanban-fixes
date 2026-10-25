#!/usr/bin/env python3
"""Deterministic allowlist ZIP builder/verifier, Python standard library only."""
import argparse
import hashlib
import os
from pathlib import Path
import re
import stat
import sys
import zipfile

from install import ROOT, package, read, safe

PUBLIC = frozenset({
    'LICENSE', 'README.md', 'CHANGELOG.md', 'manifest.json',
    'docs/INSTALL.md', 'docs/SECURITY.md', 'docs/TESTING.md',
    'tools/install.py', 'tools/package_release.py',
    'tests/test_distribution.py', 'patches/kanban-fixes.patch',
})
STAMP = (2020, 1, 1, 0, 0, 0)
MODE = (stat.S_IFREG | 0o644) << 16


def sha(data):
    return hashlib.sha256(data).hexdigest()


def checksums(files):
    return ''.join(sha(files[n]) + '  ' + n + '\n' for n in sorted(files)).encode()


def build(output):
    package()
    files = {n: read(ROOT / n) for n in sorted(PUBLIC)}
    for n, data in files.items():
        if re.search(rb'/(?:Users|home)/[^\s\x22\x27<>]+|/(?:private/)?var/folders/', data):
            raise ValueError('private absolute path in public source: ' + n)
    files['SHA256SUMS'] = checksums(files)
    output = safe(output)
    sidecar = safe(Path(str(output) + '.sha256'))
    if output.exists() or sidecar.exists():
        raise ValueError('output/archive checksum already exists')
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('xb') as f:
        with zipfile.ZipFile(f, 'w', compression=zipfile.ZIP_STORED) as z:
            for name in sorted(files):
                info = zipfile.ZipInfo(name, STAMP)
                info.create_system = 3
                info.external_attr = MODE
                info.compress_type = zipfile.ZIP_STORED
                z.writestr(info, files[name])
    verify(output)
    digest = sha(read(output))
    with sidecar.open('x') as f:
        f.write(digest + '  ' + output.name + '\n')
    return digest


def verify(archive):
    safe(archive)
    data = read(archive)
    import io
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        infos = z.infolist()
        names = [i.filename for i in infos]
        if len(names) != len(set(names)) or set(names) != PUBLIC | {'SHA256SUMS'}:
            raise ValueError('archive allowlist/duplicate mismatch')
        if names != sorted(names):
            raise ValueError('archive order is not canonical')
        for i in infos:
            if (i.date_time != STAMP or i.external_attr != MODE
                    or i.compress_type != zipfile.ZIP_STORED or i.create_system != 3
                    or i.file_size > 16 * 1024 * 1024):
                raise ValueError('noncanonical archive member')
        files = {n: z.read(n) for n in sorted(PUBLIC)}
        if z.read('SHA256SUMS') != checksums(files):
            raise ValueError('archive checksum mismatch')
        # Bind the compatibility manifest to the installer's release pin too.
        from install import MANIFEST_SHA256
        import json
        if sha(files['manifest.json']) != MANIFEST_SHA256:
            raise ValueError('archive manifest identity mismatch')
        manifest = json.loads(files['manifest.json'])
        if sha(files['patches/kanban-fixes.patch']) != manifest['patch_sha256']:
            raise ValueError('archive patch integrity mismatch')
    return sha(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--output', type=Path, help='new absolute ZIP output path')
    mode.add_argument('--verify', type=Path, help='existing absolute release ZIP')
    args = parser.parse_args()
    try:
        digest = build(args.output) if args.output else verify(args.verify)
    except (OSError, ValueError, zipfile.BadZipFile) as e:
        print('REFUSED: ' + str(e), file=sys.stderr)
        return 2
    print(digest)
    return 0


if __name__ == '__main__':
    sys.exit(main())
