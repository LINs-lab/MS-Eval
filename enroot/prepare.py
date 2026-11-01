#!/usr/bin/env python3
"""Stage pinned public sources and collect host-side Enroot runtime artifacts."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
GYM_PATHS = [
    'main.py', 'LICENSE', 'configs', 'db/init.sql.gz', 'kimi_harness',
    'local_servers', 'tasks/finalpool', 'utils', 'run_sh_eval',
    'scripts/audit_html_gen.py',
]


def git(directory, *args):
    return subprocess.check_output(['git', '-C', str(directory), *args], text=True).strip()


def check_sources():
    if sys.version_info < (3, 10):
        raise ValueError('Host Python 3.10 or newer is required')
    reference = json.loads((ROOT / 'docker/locks/reference.json').read_text())
    for name, marker in [('toolathlon_gym', 'kimi_harness/kimi_main.py'), ('kimi-code', 'pnpm-lock.yaml')]:
        directory = ROOT / name
        if not (directory / marker).is_file():
            raise ValueError('Initialize submodules: git submodule update --init --recursive')
        if git(directory, 'rev-parse', 'HEAD') != reference['sources'][name]:
            raise ValueError(f'{name} differs from docker/locks/reference.json; initialize the pinned submodules')
        if git(directory, 'diff', 'HEAD', '--name-only'):
            raise ValueError(f'{name} has tracked local edits; commit and refresh the lock before building')
    print('Pinned sources checked; no model API is used.', flush=True)


def archive(directory, destination, paths=()):
    destination.mkdir(parents=True, exist_ok=True)
    # git archive includes tracked sources only: no config.env, host dependencies or results.
    with subprocess.Popen(['git', '-C', str(directory), 'archive', 'HEAD', *paths], stdout=subprocess.PIPE) as process:
        try:
            subprocess.run(['tar', '-x', '--no-same-owner', '-C', str(destination)], stdin=process.stdout, check=True)
        finally:
            process.stdout.close()
        if process.wait():
            raise RuntimeError(f'Could not archive {directory}')


def stage(rootfs):
    check_sources()
    archive(ROOT / 'toolathlon_gym', rootfs / 'workspace', GYM_PATHS)
    archive(ROOT / 'kimi-code', rootfs / 'src/kimi-code')
    shutil.copytree(rootfs / 'workspace/local_servers', rootfs / 'opt/local_servers')
    shutil.copytree(ROOT / 'data/oracle166', rootfs / 'workspace/tasks/oracle166',
                    ignore=lambda directory, names: [n for n in names if not n.endswith('.task.md')])
    target = rootfs / 'opt/ms-eval'
    target.mkdir(parents=True)
    shutil.copytree(ROOT / 'docker/locks', target / 'locks')
    for name in ('install-runtime.py', 'verify-image.py'):
        shutil.copy2(ROOT / 'docker' / name, target / name)
    shutil.copy2(ROOT / 'enroot/provision.sh', target / 'provision.sh')
    commits = {'gym': git(ROOT / 'toolathlon_gym', 'rev-parse', 'HEAD'),
               'kimi': git(ROOT / 'kimi-code', 'rev-parse', 'HEAD')}
    (target / 'source-commits.json').write_text(json.dumps(commits, indent=2) + '\n')


def bundle(rootfs, destination):
    shutil.copytree(rootfs / 'opt/kimi-code', destination / 'kimi_dist/kimi-code', symlinks=True)
    # The runner overlays selected generated MCP files from the host onto each rootfs.
    # Store them outside the source checkout, so building cannot dirty the submodule.
    manifests = set()
    for runner in sorted((rootfs / 'workspace/run_sh_eval').glob('*/*/runner.sh')):
        manifests.add(runner.read_text().split("<<'OVERLAYS'\n", 1)[1].split('\nOVERLAYS', 1)[0])
    if len(manifests) != 1:
        raise ValueError('Expected the same Enroot overlay manifest in every preset')
    for line in manifests.pop().splitlines():
        source, target = map(Path, line.split())
        if source.is_absolute() or target.is_absolute() or '..' in source.parts or '..' in target.parts:
            raise ValueError(f'Invalid overlay path: {line}')
        if source.suffix not in ('.js', '.mjs'):
            continue
        output = destination / 'overlays' / source
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(rootfs / target, output)
    metadata = json.loads((rootfs / 'opt/ms-eval/source-commits.json').read_text())
    metadata['locks_sha256'] = hashlib.sha256((rootfs / 'opt/ms-eval/locks/reference.json').read_bytes()).hexdigest()
    (destination / 'runtime.json').write_text(json.dumps(metadata, indent=2) + '\n')
    shutil.copy2(ROOT / 'enroot/runtime-env.sh', destination / 'env.sh')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('check')
    commands.add_parser('stage').add_argument('rootfs', type=Path)
    collect = commands.add_parser('bundle')
    collect.add_argument('rootfs', type=Path)
    collect.add_argument('destination', type=Path)
    args = parser.parse_args()
    if args.command == 'check':
        check_sources()
    elif args.command == 'stage':
        stage(args.rootfs)
    else:
        bundle(args.rootfs, args.destination)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        sys.exit(2)
