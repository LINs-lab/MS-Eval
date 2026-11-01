#!/usr/bin/env bash
# Evaluate each dump in order; stop and return a nonzero status on failure.
set -euo pipefail
if [[ $# -lt 1 ]]; then
  echo "Usage: $0 DUMP_DIR [DUMP_DIR ...] [-- evaluator arguments]" >&2
  exit 2
fi
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DUMPS=()
while [[ $# -gt 0 && "$1" != "--" ]]; do
  DUMPS+=("$1")
  shift
done
if [[ $# -gt 0 ]]; then shift; fi
if [[ ${#DUMPS[@]} -eq 0 ]]; then
  echo "At least one dump directory is required." >&2
  exit 2
fi
if [[ -n "${OUT:-}" ]]; then
  echo "OUT is only supported by run_one.sh; batch outputs go into each dump." >&2
  exit 2
fi
for dump in "${DUMPS[@]}"; do
  bash "${SCRIPT_DIR}/run_one.sh" "$dump" "$@"
done
