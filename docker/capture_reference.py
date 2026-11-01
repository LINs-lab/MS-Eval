#!/usr/bin/env python3
"""Record public dependency versions from an Enroot squashfs or unpacked rootfs.

Only package metadata is read; credentials, task outputs and home files are not
copied. Run this on the cluster after deliberately updating the reference image.
"""
import argparse
import hashlib
import json
from email.parser import Parser
from pathlib import Path
import re
import subprocess
import tempfile


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def packages(venv):
    result = {}
    for path in sorted(venv.glob('lib/python*/site-packages/*.dist-info/METADATA')):
        meta = Parser().parsestr(path.read_text())
        name = re.sub(r'[-_.]+', '-', meta['Name']).lower()
        result[name] = meta['Version']
    if not result:
        raise ValueError(f'No package metadata in {venv}')
    return result


def capture(root, source, gym, kimi, output):
    output.mkdir(parents=True, exist_ok=True)
    locks = output / 'requirements'
    locks.mkdir(exist_ok=True)
    manifest = {'schema': 1, 'reference': source, 'environments': {}}
    for key, path in [('harness', root / 'opt/venv'), *[
        (p.parent.name, p) for p in sorted((root / 'opt/local_servers').glob('*/.venv'))
    ]]:
        versions = packages(path)
        config = dict(line.split(' = ', 1) for line in (path / 'pyvenv.cfg').read_text().splitlines() if ' = ' in line)
        local = None
        if key != 'harness':
            source_project = (gym / 'local_servers' / key / 'pyproject.toml').read_text()
            local = re.search(r'(?m)^name\s*=\s*"([^"]+)"', source_project).group(1)
            versions.pop(re.sub(r'[-_.]+', '-', local).lower(), None)
        lock = locks / f'{key}.txt'
        lock.write_text('# Captured from the reference Enroot image; regenerate with capture_reference.py.\n' +
                        ''.join(f'{name}=={version}\n' for name, version in sorted(versions.items())))
        manifest['environments'][key] = {'python': config['version_info'], 'local_project': local,
                                         'requirements_sha256': digest(lock)}
    header = (root / 'usr/local/include/node/node_version.h').read_text()
    manifest['node'] = '.'.join(re.search(rf'#define NODE_{part}_VERSION (\d+)', header).group(1)
                                for part in ('MAJOR', 'MINOR', 'PATCH'))
    manifest['uv'] = dict(line.split(' = ', 1) for line in
                          (root / 'opt/venv/pyvenv.cfg').read_text().splitlines() if ' = ' in line)['uv']
    manifest['sources'] = {}
    for name, directory in [('toolathlon_gym', gym), ('kimi-code', kimi)]:
        commit = subprocess.check_output(['git', '-C', str(directory), 'rev-parse', 'HEAD'], text=True).strip()
        manifest['sources'][name] = commit
    manifest['database_seed_sha256'] = digest(gym / 'db/init.sql.gz')
    manifest['tasks_sha256'] = digest(gym / 'run_sh_eval/claude-sonnet-5/spec/tasks.txt')
    manifest['npm_fallbacks'] = {}
    for project in sorted((gym / 'local_servers').glob('*/package.json')):
        current = json.loads(project.read_text())
        source_lock = project.parent / 'package-lock.json'
        if source_lock.exists():
            locked = json.loads(source_lock.read_text()).get('packages', {}).get('', {})
            if all(locked.get(k, {}) == current.get(k, {}) for k in ('dependencies', 'devDependencies')):
                continue
        name = project.parent.name
        lock = root / 'opt/local_servers' / name / 'package-lock.json'
        if not lock.is_file():
            raise ValueError(f'Missing reference npm lock: {name}')
        snapshot = json.loads(lock.read_text())
        # Some public package-lock roots predate the PG adapter dependencies.
        # Retain the reference's fully resolved tree, updating only the root's
        # declared ranges; npm ci still checks every required version at build.
        for key in ('dependencies', 'devDependencies'):
            snapshot['packages'][''][key] = current.get(key, {})
        destination = output / 'npm' / (name + '.json')
        destination.parent.mkdir(exist_ok=True)
        destination.write_text(json.dumps(snapshot, indent=2) + '\n')
        manifest['npm_fallbacks'][name] = digest(destination)
    (output / 'reference.json').write_text(json.dumps(manifest, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--sqsh', type=Path)
    source.add_argument('--rootfs', type=Path)
    parser.add_argument('--gym', type=Path, default=Path(__file__).resolve().parents[1] / 'toolathlon_gym')
    parser.add_argument('--kimi', type=Path, default=Path(__file__).resolve().parents[1] / 'kimi-code')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.rootfs:
        capture(args.rootfs, {'kind': 'rootfs', 'name': args.rootfs.name}, args.gym, args.kimi, args.out)
    else:
        with tempfile.TemporaryDirectory(prefix='mse-reference-') as temp:
            root = Path(temp) / 'rootfs'
            subprocess.run(['unsquashfs', '-processors', '2', '-no-progress', '-no-xattrs',
                            '-d', str(root), str(args.sqsh),
                            'opt/venv/pyvenv.cfg', 'opt/venv/lib/python*/site-packages/*.dist-info/METADATA',
                            'opt/local_servers/*/.venv/pyvenv.cfg',
                            'opt/local_servers/*/.venv/lib/python*/site-packages/*.dist-info/METADATA',
                            'opt/local_servers/*/package-lock.json',
                            'usr/local/include/node/node_version.h'], check=True)
            capture(root, {'kind': 'sqsh', 'name': args.sqsh.name},
                    args.gym, args.kimi, args.out)


if __name__ == '__main__':
    main()
