#!/usr/bin/env python3
"""Build environments from recorded Enroot package versions, without host venvs."""
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import urllib.request

ROOT = Path('/opt/ms-eval')
REFERENCE = json.loads((ROOT / 'locks/reference.json').read_text())


def run(*args, **kwargs):
    print('+', *map(str, args), flush=True)
    subprocess.run(list(map(str, args)), check=True, **kwargs)


def bootstrap():
    arch = {'x86_64': 'x64', 'aarch64': 'arm64'}.get(platform.machine())
    if not arch:
        raise SystemExit('Supported image architectures: linux/amd64 and linux/arm64')
    version = REFERENCE['node']
    name = f'node-v{version}-linux-{arch}.tar.xz'
    base = os.environ.get('NODE_MIRROR', 'https://nodejs.org/dist').rstrip('/') + f'/v{version}'
    urllib.request.urlretrieve(base + '/' + name, '/tmp/' + name)
    sums = urllib.request.urlopen(base + '/SHASUMS256.txt', timeout=60).read().decode().splitlines()
    expected = next(line.split()[0] for line in sums if line.split()[-1] == name)
    assert hashlib.sha256(Path('/tmp', name).read_bytes()).hexdigest() == expected, 'Node checksum mismatch'
    run('tar', '-xJf', '/tmp/' + name, '-C', '/usr/local', '--strip-components=1')
    Path('/tmp', name).unlink()
    # uv's PyPI wheel carries the executable, avoiding an unversioned curl|sh.
    run(sys.executable, '-m', 'pip', 'install', '--no-cache-dir', '--timeout', '60',
        '--index-url', os.environ.get('UV_INDEX_URL', 'https://pypi.org/simple'), f"uv=={REFERENCE['uv']}")


def dependencies():
    for name, config in REFERENCE['environments'].items():
        lock = ROOT / 'locks/requirements' / f'{name}.txt'
        assert hashlib.sha256(lock.read_bytes()).hexdigest() == config['requirements_sha256'], name
        python = config['python']
        # The reference Excel environment used Ubuntu's system Python 3.10.
        interpreter = '/usr/bin/python3' if python.startswith('3.10.') else python
        if interpreter == python:
            run('uv', 'python', 'install', python)
        directory = Path('/opt/local_servers') / name
        venv = Path('/opt/venv') if name == 'harness' else directory / '.venv'
        run('uv', 'venv', '--python', interpreter, venv)
        run('uv', 'pip', 'install', '--python', venv / 'bin/python', '--no-deps', '-r', lock)
        if config['local_project']:
            run('uv', 'pip', 'install', '--python', venv / 'bin/python', '--no-deps', '-e', directory)
        run('uv', 'pip', 'check', '--python', venv / 'bin/python')
    for directory in sorted(Path('/opt/local_servers').iterdir()):
        if not (directory / 'package.json').is_file():
            continue
        backup = ROOT / 'locks/npm' / (directory.name + '.json')
        if backup.exists():
            assert hashlib.sha256(backup.read_bytes()).hexdigest() == REFERENCE['npm_fallbacks'][directory.name]
            shutil.copyfile(backup, directory / 'package-lock.json')
        if not (directory / 'package-lock.json').exists():
            raise RuntimeError(f'Missing npm lock for {directory.name}')
        run('npm', 'ci', '--ignore-scripts', '--no-audit', '--no-fund',
            '--registry', os.environ.get('NPM_REGISTRY', 'https://registry.npmjs.org'), cwd=directory)
        run('npm', 'run', 'build', cwd=directory)


if __name__ == '__main__':
    {'bootstrap': bootstrap, 'dependencies': dependencies}[sys.argv[1]]()
