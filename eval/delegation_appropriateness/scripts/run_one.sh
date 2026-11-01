#!/usr/bin/env bash
# Evaluate one experiment. Extra arguments are passed to the DA evaluator.
set -euo pipefail
if [[ $# -lt 1 ]]; then
  echo "Usage: $0 DUMP_DIR [--match] [other evaluator arguments]" >&2
  exit 2
fi
DUMP="$1"
shift
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
ARGS=(--dump "$DUMP" --out "${OUT:-$DUMP}" --workers "${WORKERS:-6}")
[[ -z "${GT_PATH:-}" ]] || ARGS+=(--gt-path "$GT_PATH")
[[ -z "${CACHE:-}" ]] || ARGS+=(--cache "$CACHE")
[[ -z "${KEY_FILE:-}" ]] || ARGS+=(--llm-key "$KEY_FILE")
exec "${PYTHON_BIN:-python3}" "${REPO_ROOT}/eval/delegation_appropriateness/evaluate.py" "${ARGS[@]}" "$@"
