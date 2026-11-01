#!/usr/bin/env bash
# Native Enroot build; shares dependency locks and verification with Docker.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
usage() {
  cat <<'EOF'
Usage: bash enroot/build.sh [--output DIR] [--base-image FILE] [--check]
  --output DIR       Runtime bundle (default: MS-Eval/.local/enroot)
  --base-image FILE   Existing Ubuntu 22.04 amd64 Enroot image; otherwise import it
  --check            Check host tools and pinned sources without building
Environment: ENROOT_INSTALL_ROOT, TMPDIR, ENROOT_MAX_PROCESSORS (default: 4).
EOF
}
OUTPUT="$ROOT/.local/enroot"
BASE_IMAGE=""
CHECK=0
while (($#)); do
  case "$1" in
    --output|--base-image)
      [[ $# -ge 2 && -n "$2" ]] || { usage >&2; exit 2; }
      if [[ "$1" == --output ]]; then OUTPUT="$2"; else BASE_IMAGE="$2"; fi
      shift 2 ;;
    --check) CHECK=1; shift ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done
[[ $(uname -m) == x86_64 ]] || { echo 'This build requires Linux x86-64.' >&2; exit 2; }
if [[ -z "${ENROOT_INSTALL_ROOT:-}" ]]; then
  executable="$(command -v enroot || true)"
  if [[ -n "$executable" && "$(basename -- "$(readlink -f -- "$executable")")" == enroot-wrapper ]]; then
    ENROOT_INSTALL_ROOT="$(dirname -- "$(dirname -- "$(readlink -f -- "$executable")")")"
  fi
fi
if [[ -n "${ENROOT_INSTALL_ROOT:-}" ]]; then
  export PATH="$ENROOT_INSTALL_ROOT/bin:$PATH"
  export ENROOT_LIBRARY_PATH="$ENROOT_INSTALL_ROOT/lib"
  export ENROOT_SYSCONF_PATH="$ENROOT_INSTALL_ROOT/etc"
fi
for tool in enroot python3 git rsync mksquashfs unsquashfs timeout; do
  command -v "$tool" >/dev/null || { echo "Missing host tool: $tool" >&2; exit 2; }
done
timeout 15 enroot version
python3 "$ROOT/enroot/prepare.py" check
((CHECK == 0)) || exit 0
OUTPUT="$(python3 -c 'import pathlib,sys; print(pathlib.Path(sys.argv[1]).resolve())' "$OUTPUT")"
[[ ! -e "$OUTPUT" && ! -L "$OUTPUT" ]] || {
  echo "Output already exists: $OUTPUT; choose a new --output directory." >&2; exit 2;
}
mkdir -p -- "$(dirname -- "$OUTPUT")"
BUNDLE="$(mktemp -d "${OUTPUT}.build.XXXXXX")"
WORK=""
cleanup() {
  [[ -z "$WORK" ]] || rm -rf -- "$WORK"
  [[ -z "$BUNDLE" ]] || rm -rf -- "$BUNDLE"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
WORK="$(mktemp -d "${TMPDIR:-/tmp}/mse-enroot.XXXXXX")"
export ENROOT_DATA_PATH="$WORK/data" ENROOT_TEMP_PATH="$WORK/tmp"
export ENROOT_RUNTIME_PATH="$WORK/run" ENROOT_CACHE_PATH="$WORK/cache"
export ENROOT_CONFIG_PATH="$WORK/config" ENROOT_MOUNT_HOME=no
export ENROOT_MAX_PROCESSORS="${ENROOT_MAX_PROCESSORS:-4}"
mkdir -p "$ENROOT_DATA_PATH" "$ENROOT_TEMP_PATH" "$ENROOT_RUNTIME_PATH" "$ENROOT_CACHE_PATH" "$ENROOT_CONFIG_PATH"
if [[ -z "$BASE_IMAGE" ]]; then
  BASE_IMAGE="$WORK/ubuntu-22.04.sqsh"
  enroot import -o "$BASE_IMAGE" docker://docker.io#ubuntu:22.04
else
  BASE_IMAGE="$(realpath -- "$BASE_IMAGE")"
fi
enroot create -n ms-eval-build "$BASE_IMAGE"
# Fail early if the host cannot create the namespaces needed by Enroot.
enroot start --root --rw ms-eval-build /bin/true
python3 "$ROOT/enroot/prepare.py" stage "$ENROOT_DATA_PATH/ms-eval-build"
BUILD_ENV=()
for key in http_proxy https_proxy HTTP_PROXY HTTPS_PROXY no_proxy NO_PROXY \
           NPM_REGISTRY NODE_MIRROR UV_INDEX_URL UV_PYTHON_INSTALL_MIRROR PLAYWRIGHT_DOWNLOAD_HOST; do
  [[ ! -v "$key" ]] || BUILD_ENV+=(-e "$key")
done
enroot start --root --rw "${BUILD_ENV[@]}" ms-eval-build /bin/bash /opt/ms-eval/provision.sh
enroot start --root --rw ms-eval-build /opt/venv/bin/python /opt/ms-eval/verify-image.py
mkdir -p "$BUNDLE/images"
enroot export -o "$BUNDLE/images/toolathlon-pack.sqsh" ms-eval-build
unsquashfs -s "$BUNDLE/images/toolathlon-pack.sqsh" >/dev/null
python3 "$ROOT/enroot/prepare.py" bundle "$ENROOT_DATA_PATH/ms-eval-build" "$BUNDLE"
mv -T -- "$BUNDLE" "$OUTPUT"
BUNDLE=""
printf 'Enroot runtime ready: %s\n' "$OUTPUT"
