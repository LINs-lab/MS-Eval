#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
ENGINE="${CONTAINER_ENGINE:-docker}"
IMAGE="${MSE_IMAGE:-ms-eval:local}"
DB_IMAGE="${MSE_DB_IMAGE:-ms-eval-db:local}"
case "$ENGINE" in docker|podman) ;; *) echo 'CONTAINER_ENGINE must be docker or podman' >&2; exit 2;; esac
command -v "$ENGINE" >/dev/null || { echo "$ENGINE is not installed" >&2; exit 2; }
for path in toolathlon_gym/kimi_harness/kimi_main.py kimi-code/pnpm-lock.yaml; do
  [[ -f "$ROOT/$path" ]] || { echo 'Initialize submodules: git submodule update --init --recursive' >&2; exit 2; }
done
for path in toolathlon_gym kimi-code; do
  if [[ -n "$(git -C "$ROOT/$path" diff HEAD --name-only)" ]]; then
    echo "$path has tracked local edits; use a clean checkout, or commit and refresh the reference before building." >&2
    exit 2
  fi
done
GYM_COMMIT="$(git -C "$ROOT/toolathlon_gym" rev-parse HEAD)"
KIMI_COMMIT="$(git -C "$ROOT/kimi-code" rev-parse HEAD)"
DATABASE_SEED_SHA256="$(sha256sum "$ROOT/toolathlon_gym/db/init.sql.gz" | cut -d ' ' -f 1)"
# Refuse accidental submodule upgrades: update the reference deliberately.
for revision in "$GYM_COMMIT" "$KIMI_COMMIT"; do
  grep -Fq '"'"$revision"'"' "$ROOT/docker/locks/reference.json" || {
    echo 'Submodule revision differs from docker/locks/reference.json; initialize the pinned sources with git submodule update --init --recursive.' >&2
    exit 2
  }
done
"$ENGINE" info >/dev/null
cd "$ROOT"
"$ENGINE" build -f docker/Dockerfile --target evaluator -t "$IMAGE" \
  --build-arg "GYM_COMMIT=$GYM_COMMIT" --build-arg "KIMI_COMMIT=$KIMI_COMMIT" "$@" .
"$ENGINE" build -f docker/Dockerfile --target database -t "$DB_IMAGE" \
  --build-arg "DATABASE_SEED_SHA256=$DATABASE_SEED_SHA256" "$@" .
"$ENGINE" run --rm --network none "$IMAGE" /opt/venv/bin/python /opt/ms-eval/verify-image.py
echo "Built and verified $IMAGE and $DB_IMAGE"
