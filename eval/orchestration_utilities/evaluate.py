#!/usr/bin/env python3
"""Compute U_p, U_e, and U_c for one MAD-SAE / SA experiment pair."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from eval.common.paths import DEFAULT_GT
from eval.delegation_appropriateness.rates import load_delegated_from_task_metrics, load_gt_need
from eval.orchestration_utilities.metrics import load_summary_csv, utilities


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mad", type=Path, required=True, help="MAD-SAE experiment directory")
    parser.add_argument("--sa", type=Path, required=True, help="SA baseline experiment directory")
    parser.add_argument("--da", type=Path, help="DA output directory (default: --mad)")
    parser.add_argument("--gt-index", type=Path, default=DEFAULT_GT / "_index.json")
    parser.add_argument("--out", type=Path, help="Output JSON file (default: stdout)")
    parser.add_argument("--include-failed", action="store_true",
                        help="Diagnostic only: include MAD failures in resource averages")
    args = parser.parse_args()
    mad = load_summary_csv(args.mad / "summary.csv")
    sa = load_summary_csv(args.sa / "summary.csv")
    if not mad or not sa:
        parser.error("Both experiment directories must contain a nonempty summary.csv.")
    da_dir = args.da or args.mad
    if not (da_dir / "task_metrics.json").is_file():
        parser.error(f"Missing {da_dir / 'task_metrics.json'}; run DA evaluation first.")
    gt_need = load_gt_need(args.gt_index)
    observed = load_delegated_from_task_metrics(da_dir)
    delegated = {t: value for t, value in observed.items() if t in gt_need}
    result = {
        "scope": "all_delegated_diagnostic" if args.include_failed else "mad_successful_delegated",
        "n_missing_da": sum(t not in delegated for t in gt_need),
        "missing_paired_tasks": sorted(t for t, value in delegated.items()
                                       if value and (t not in mad or t not in sa)),
        "utilities": utilities(mad, sa, args.include_failed, delegated),
    }
    body = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(body, encoding="utf-8")
    else:
        print(body, end="")


if __name__ == "__main__":
    main()
