#!/usr/bin/env bash
# Copied into the generated bundle as env.sh; source it before running evaluations.
export RUNTIME_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export AGENT_SQSH="$RUNTIME_ROOT/images/toolathlon-pack.sqsh"
export AGENT_TEMPLATE=""
export KIMI_DIST="$RUNTIME_ROOT/kimi_dist/kimi-code"
# Debian/Ubuntu install PostgreSQL server tools outside the default PATH.
if ! command -v initdb >/dev/null 2>&1; then
  if [[ -x /usr/lib/postgresql/15/bin/initdb ]]; then
    export PATH="/usr/lib/postgresql/15/bin:$PATH"
  elif command -v pg_config >/dev/null 2>&1; then
    mse_pg_bin="$(pg_config --bindir)"
    [[ ! -x "$mse_pg_bin/initdb" ]] || export PATH="$mse_pg_bin:$PATH"
    unset mse_pg_bin
  fi
fi
