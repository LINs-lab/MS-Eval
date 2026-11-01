#!/usr/bin/env python3
"""Combine DA, OU, and equal-weight MSQ into a Markdown results table.

Read <root>/<model>/<variant>/summary.csv and each MAD experiment's DA outputs
(summary.json and task_metrics.json). Use sa/ (or the paper-era single/) as the
SA baseline.
MSQ = LLM-reviewed hit F1 * (U_p + U_e + U_c) / 3. A missing LLM F1 leaves MSQ
undefined. Historical LLM-reviewed reports remain readable."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eval.common.paths import DEFAULT_GT
from eval.delegation_appropriateness.rates import (
    delegation_rates, load_delegated_from_task_metrics, load_gt_need,
)
from eval.orchestration_utilities.metrics import load_summary_csv, utilities

DEFAULT_GT_INDEX = DEFAULT_GT / "_index.json"

# Launcher variant names, followed by their paper-era directory names.
SA_SUBDIRS = ("sa", "single")
MAIN_MAD = ("spec", "auto-spec")  # Listed last for each model.
EXTRA_MAD = [  # Study configurations, listed first.
    "gen", "auto-gen",
    "plan1st",
    "oracle", "oracle-spec",
]
SKIP_MAD = {"deprecated-oracle"}  # Legacy, non-reporting configuration.


def load_hit_prf(dump: Path) -> tuple[float | None, float | None, float | None]:
    p = dump / "summary.json"
    if not p.is_file():
        return None, None, None
    try:
        s = json.loads(p.read_text())
        if s.get("label_source") == "llm":
            st = s.get("hit_scores") or {}
        else:
            # Read historical LLM-reviewed reports without accepting seed-label scores.
            st = (s.get("llm") or {}).get("strict") or {}
        return st.get("precision"), st.get("recall"), st.get("f1")
    except Exception:
        return None, None, None


def main():
    ap = argparse.ArgumentParser(description="Combine DA, OU, and equal-weight MSQ into a Markdown table.")
    ap.add_argument("--root", type=Path, required=True, help="Directory containing <model>/<variant>/summary.csv")
    ap.add_argument("--gt-index", type=Path, default=DEFAULT_GT_INDEX)
    ap.add_argument(
        "--model",
        action="append",
        default=None,
        help="Select a model directory; repeat for multiple models (default: all).",
    )
    ap.add_argument(
        "--include-failed",
        action="store_true",
        help="Diagnostic only: include MAD failures in U_e/U_c (not the paper protocol).",
    )
    args = ap.parse_args()

    gt_need = load_gt_need(args.gt_index)

    models = sorted(p.name for p in args.root.iterdir() if p.is_dir() and not p.name.startswith("."))
    if args.model:
        models = [m for m in models if m in set(args.model)]

    scope_label = "D_del (including MAD failures; diagnostic)" if args.include_failed else "D_del intersect MAD success"
    print(f"<!-- U_e / U_c scope: {scope_label} -->")
    cols = [
        "experiment", "P_hit", "R_hit", "F1_hit",
        "UDR", "ODR",
        "U_p", "U_e", "U_c", "MSQ",
    ]
    print("| " + " | ".join(cols) + " |")
    print("|" + "|".join(["---"] * len(cols)) + "|")

    def fmt_pct(x):
        return "-" if x is None else f"{x*100:.2f}%"

    def fmt4(x):
        return "-" if x is None else f"{x:.4f}"

    for model in models:
        mdir = args.root / model
        subs = sorted(p.name for p in mdir.iterdir() if p.is_dir() and not p.name.startswith("."))
        sa_rows = next((rows for rows in (load_summary_csv(mdir / s / "summary.csv")
                                          for s in SA_SUBDIRS) if rows), {})

        mad_experiments = [s for s in subs if s not in SA_SUBDIRS and s not in SKIP_MAD]
        ordered = [e for e in EXTRA_MAD if e in mad_experiments] + \
                  [e for e in mad_experiments if e not in EXTRA_MAD and e not in MAIN_MAD] + \
                  [e for e in MAIN_MAD if e in mad_experiments]

        for exp in ordered:
            dump = mdir / exp
            rows = load_summary_csv(dump / "summary.csv")
            if not rows:
                continue
            P, R, F1 = load_hit_prf(dump)
            if not (dump / "task_metrics.json").is_file():
                ap.error(f"Missing {dump / 'task_metrics.json'}; run DA evaluation first.")
            delegated_map = load_delegated_from_task_metrics(dump)
            delegated_map = {t: value for t, value in delegated_map.items() if t in gt_need}
            uo = delegation_rates(gt_need, delegated_map)
            if uo["n_missing"]:
                print(f"[warn] {model}/{exp}: {uo['n_missing']} tasks lack DA coverage", file=sys.stderr)
            missing_pairs = [t for t, value in delegated_map.items()
                             if value and (t not in rows or t not in sa_rows)]
            if missing_pairs:
                print(f"[warn] {model}/{exp}: {len(missing_pairs)} delegated tasks lack paired summaries", file=sys.stderr)
            util = utilities(
                rows, sa_rows,
                include_failed=args.include_failed,
                delegated_map=delegated_map,
            ) if sa_rows else None

            udr_s = (
                f"{fmt_pct(uo['udr'])} ({uo['udr_cnt']}/{uo['n_need']})"
                if uo["udr"] is not None else "-"
            )
            odr_s = (
                f"{fmt_pct(uo['odr'])} ({uo['odr_cnt']}/{uo['n_noneed']})"
                if uo["odr"] is not None else "-"
            )

            if util:
                u_parts = [util[k] for k in ("U_p", "U_e", "U_c")]
                msq = (F1 * sum(u_parts) / 3) if (
                    F1 is not None and all(v is not None for v in u_parts)
                ) else None

                u_p_s = (
                    f"{fmt4(util['U_p'])} "
                    f"({util['mad_succ_cnt']}/{util['sa_succ_cnt']})"
                    if util["U_p"] is not None else "-"
                )
                u_e_s = (
                    f"{fmt4(util['U_e'])} "
                    f"({util['cs_mad']:.2f}/{util['cs_sa']:.2f})"
                    if util["U_e"] is not None else "-"
                )
                u_c_s = (
                    f"{fmt4(util['U_c'])} "
                    f"(${util['c_mad']:.4f}/${util['c_sa']:.4f})"
                    if util["U_c"] is not None else "-"
                )
                msq_s = fmt4(msq)
            else:
                u_p_s = u_e_s = u_c_s = msq_s = "-"

            name = f"{model}/{exp}"
            row = [
                name,
                fmt_pct(P), fmt_pct(R), fmt_pct(F1),
                udr_s, odr_s,
                u_p_s, u_e_s, u_c_s, msq_s,
            ]
            print("| " + " | ".join(row) + " |")


if __name__ == "__main__":
    main()
