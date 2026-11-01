#!/usr/bin/env bash
# Compute utilities from an experiment pair and existing DA output.
set -euo pipefail
if [[ $# -lt 2 ]]; then
  echo "Usage: $0 MAD_DIR SA_DIR [other evaluator arguments]" >&2
  exit 2
fi
MAD_DIR="$1"
SA_DIR="$2"
shift 2
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
exec "${PYTHON_BIN:-python3}" "${REPO_ROOT}/eval/orchestration_utilities/evaluate.py" --mad "$MAD_DIR" --sa "$SA_DIR" "$@"
