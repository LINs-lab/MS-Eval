#!/usr/bin/env bash
# Runs inside the writable Ubuntu rootfs, never on the host.
set -euo pipefail
[[ -f /opt/ms-eval/source-commits.json && -d /src/kimi-code ]] || exit 2
source /etc/os-release
[[ "$ID" == ubuntu && "$VERSION_ID" == 22.04 ]] || {
  echo 'The base image must be Ubuntu 22.04.' >&2; exit 2;
}
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends \
  ca-certificates curl git xz-utils python3 python3-pip python3-venv \
  build-essential pkg-config libffi-dev libssl-dev libseccomp2 bubblewrap \
  postgresql-client rsync lsof psmisc procps iproute2 util-linux \
  poppler-utils qpdf fonts-liberation fonts-noto-cjk zip unzip file tree tini
python3 /opt/ms-eval/install-runtime.py bootstrap
export UV_PYTHON_INSTALL_DIR=/opt/uv_python_cache
export PATH=/opt/venv/bin:/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin
export PLAYWRIGHT_BROWSERS_PATH=/opt/ms-playwright
python3 /opt/ms-eval/install-runtime.py dependencies
/opt/venv/bin/playwright install-deps chromium
/opt/venv/bin/playwright install chromium
(cd /opt/local_servers/playwright-mcp && node node_modules/playwright/cli.js install chromium)

# Kimi builds with Node 24; the evaluation runtime stays on the locked Node 22.
python3 - <<'PY'
import hashlib
import os
from pathlib import Path
import subprocess
import urllib.request
version = '24.15.0'
filename = f'node-v{version}-linux-x64.tar.xz'
base = os.environ.get('NODE_MIRROR', 'https://nodejs.org/dist').rstrip('/') + '/v' + version
archive = Path('/tmp') / filename
urllib.request.urlretrieve(base + '/' + filename, archive)
sums = urllib.request.urlopen(base + '/SHASUMS256.txt', timeout=60).read().decode().splitlines()
expected = next(line.split()[0] for line in sums if line.split()[-1] == filename)
assert hashlib.sha256(archive.read_bytes()).hexdigest() == expected, 'Build Node checksum mismatch'
Path('/opt/build-node').mkdir()
subprocess.run(['tar', '-xJf', str(archive), '-C', '/opt/build-node', '--strip-components=1'], check=True)
archive.unlink()
PY
(
  export PATH=/opt/build-node/bin:$PATH
  export npm_config_registry="${NPM_REGISTRY:-https://registry.npmjs.org}"
  export CI=true SKIP_INSTALL_SIMPLE_GIT_HOOKS=1 PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
  cd /src/kimi-code
  npm install --global pnpm@10.33.0
  pnpm install --frozen-lockfile
  pnpm run build:packages
  pnpm --filter @moonshot-ai/kimi-code run build
  test -s apps/kimi-code/dist/main.mjs
  mkdir -p /opt/kimi-code
  cp -a apps/kimi-code/{dist,dist-web,native,package.json} /opt/kimi-code/
)
mkdir -p /workspace/scripts /workspace/dumps
printf '#!/bin/sh\nexec /usr/local/bin/node /opt/kimi-code/dist/main.mjs "$@"\n' > /usr/local/bin/kimi
chmod +x /usr/local/bin/kimi
cat > /etc/environment <<'EOF'
PATH=/opt/venv/bin:/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin
HOME=/root
TZ=UTC
PGTZ=UTC
VIRTUAL_ENV=/opt/venv
PYTHON_BIN=/opt/venv/bin/python3
LOCAL_SERVERS_PATH=/opt/local_servers
UV_PYTHON_INSTALL_DIR=/opt/uv_python_cache
UV_NO_SYNC=true
UV_OFFLINE=true
UV_FROZEN=true
PLAYWRIGHT_BROWSERS_PATH=/opt/ms-playwright
PLAYWRIGHT_MCP_SANDBOX=false
KIMI_CODE_BUILTIN_PRODUCT_SKILLS=0
EOF
rm -rf /src/kimi-code /opt/build-node /root/.cache /root/.npm /root/.local/share/pnpm /var/lib/apt/lists/*
