#!/usr/bin/env python3
"""Offline, build-time image gates. Every failed check stops the build."""
import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path('/opt/ms-eval')
NODE_ENTRIES = {
    'Calendar-Autoauth-MCP-Server': 'build/index.js', 'google-forms-mcp': 'build/index.js',
    'youtube-mcp-server': 'dist/index.js', 'mcp-canvas-lms': 'build/index.js',
    '12306-mcp': 'build/index.js', 'filesystem': 'dist/index.js',
    'HowToCook-mcp': 'build/index.js', 'servers': 'src/memory/dist/index.js',
    'mcp-npx-fetch': 'dist/index.js', 'notion-mcp-server': 'bin/cli.mjs',
    'woocommerce-mcp': 'dist/index.js', 'playwright-mcp': 'cli.js',
}
PYTHON_IMPORTS = {
    'excel-mcp-server': 'excel_mcp', 'Office-Word-MCP-Server': 'word_document_server.main',
    'Office-PowerPoint-MCP-Server': 'ppt_mcp_server', 'cli-mcp-server': 'cli_mcp_server',
    'emails-mcp': 'emails_mcp.server', 'arxiv-mcp-server': 'arxiv_mcp_server',
    'arxiv-latex-mcp': 'arxiv_to_prompt', 'mcp-scholarly': 'mcp_scholarly',
    'mcp-snowflake-server': 'mcp_snowflake_server', 'pdf-tools-mcp': 'pdf_tools_mcp',
    'mcp-youtube-transcript': 'mcp_youtube_transcript', 'mcp-google-sheets': 'mcp_google_sheets',
    'yahoo-finance-mcp': 'pandas,psycopg2,yfinance',
}


def run(*args, **kwargs):
    subprocess.run(args, check=True, timeout=120, **kwargs)


def main():
    ref = json.loads((ROOT / 'locks/reference.json').read_text())
    assert subprocess.check_output(['node', '--version'], text=True).strip() == 'v' + ref['node']
    assert subprocess.check_output(['uv', '--version'], text=True).split()[1] == ref['uv']
    for name, config in ref['environments'].items():
        venv = Path('/opt/venv') if name == 'harness' else Path('/opt/local_servers') / name / '.venv'
        # Compare the installed metadata, not just the presence of lockfiles.
        run(str(venv / 'bin/python'), '-c',
            "import importlib.metadata as m, pathlib, sys; "
            "pins=[line.split('==') for line in pathlib.Path(sys.argv[1]).read_text().splitlines() "
            "if line and not line.startswith('#')]; "
            "mismatches=[(name, version, m.version(name)) for name, version in pins if m.version(name)!=version]; "
            "assert not mismatches, mismatches; "
            "assert sys.version.split()[0].startswith(sys.argv[2]), sys.version",
            str(ROOT / 'locks/requirements' / (name + '.txt')),
            '3.10.' if name == 'excel-mcp-server' else config['python'])
    for path, expected in [('db/init.sql.gz', ref['database_seed_sha256']),
                           ('run_sh_eval/claude-sonnet-5/spec/tasks.txt', ref['tasks_sha256'])]:
        assert hashlib.sha256((Path('/workspace') / path).read_bytes()).hexdigest() == expected, path
    for name, entry in NODE_ENTRIES.items():
        path = Path('/opt/local_servers') / name / entry
        assert path.is_file(), path
        run('node', '--check', str(path), stdout=subprocess.DEVNULL)
    for name, modules in PYTHON_IMPORTS.items():
        python = Path('/opt/local_servers') / name / '.venv/bin/python'
        run(str(python), '-c', 'import ' + modules, env=dict(os.environ, ALLOWED_DIR='/tmp'),
            cwd=str(python.parents[2]))
    markers = {
        'notion-mcp-server/bin/cli.mjs': 'PgHttpClient',
        'mcp-canvas-lms/build/client.js': 'Using PgCanvasRouter',
        'mcp-canvas-lms/build/index.js': 'Results are paginated and include summary totals',
        'Calendar-Autoauth-MCP-Server/build/index.js': 'toUtcIso',
    }
    for path, marker in markers.items():
        assert marker in (Path('/opt/local_servers') / path).read_text(), path
    assert Path('/opt/local_servers/woocommerce-mcp/dist/services/pg-rest-server.js').is_file()
    for name in ['camel', 'mcp', 'anthropic', 'psycopg2', 'openpyxl', 'docx', 'pptx', 'pypdf', 'yaml']:
        importlib.import_module(name)
    sys.path.insert(0, '/workspace')
    importlib.import_module('kimi_harness.kimi_main')
    importlib.import_module('utils.evaluation.evaluator')
    from importlib.metadata import version
    assert version('mcp').startswith('1.'), 'Harness requires MCP 1.x'
    for venv in [Path('/opt/venv'), *Path('/opt/local_servers').glob('*/.venv')]:
        for entry in (venv / 'bin').iterdir():
            if entry.is_symlink():
                assert entry.exists(), f'Broken interpreter link: {entry}'
            elif entry.is_file():
                with entry.open('rb') as stream:
                    first = stream.readline(512)
                if first.startswith(b'#!'):
                    interpreter = first[2:].split()[0].decode()
                    assert Path(interpreter).is_file(), f'Host interpreter leaked into {entry}'
    run('kimi', '--version')
    help_text = subprocess.check_output(['kimi', '--help'], text=True, timeout=60)
    assert '--agent-file' in help_text and '--output-format' in help_text
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=['--no-sandbox'])
        page = browser.new_page()
        page.set_content('<title>MS-Eval offline</title>')
        assert page.title() == 'MS-Eval offline'
        browser.close()
    run('node', '--input-type=module', '-e',
        "import {chromium} from 'playwright'; const b=await chromium.launch({headless:true,args:['--no-sandbox']}); await b.close();",
        cwd='/opt/local_servers/playwright-mcp')
    print('MS-Eval image: dependencies, fixtures, MCP builds, Kimi and both Chromium versions OK')


if __name__ == '__main__':
    main()
