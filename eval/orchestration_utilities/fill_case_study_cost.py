#!/usr/bin/env python3
"""Export per-task cost case studies as relative Markdown links.

Read paired MAD-SAE/SA summary.csv files and non-planning delegation decisions
from DA task_metrics.json. Group cases by MAD success and cost advantage.
These diagnostic case lists include failures; paper U_e/U_c do not.
The experiment list below retains the original study configurations."""
from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from eval.delegation_appropriateness.rates import load_delegated_from_task_metrics

EXPERIMENTS = [
    ("claude-sonnet-5", "auto-spec"),
    ("deepseek-v4-flash-0731", "auto-gen"),
    ("deepseek-v4-flash-0731", "auto-spec"),
    ("deepseek-v4-flash-0731", "oracle-spec"),
    ("deepseek-v4-flash-0731", "plan1st"),
    ("glm-5.3", "auto-spec"),
    ("glm-5.3-flash", "auto-spec"),
    ("gpt-5.6-sol", "auto-spec"),
    ("kimi-k3", "auto-spec"),
    ("minimax-m3", "auto-spec"),
    ("qwen-3.8-max", "auto-spec"),
]


def _to_int(x, default=0):
    try:
        return int(str(x).strip())
    except Exception:
        return default


def _to_float(x, default=0.0):
    try:
        return float(str(x).strip())
    except Exception:
        return default


def load_summary(path: Path) -> dict[str, dict]:
    if not path.is_file():
        return {}
    out = {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            t = (r.get("Task") or "").strip()
            if not t:
                continue
            audit = (r.get("audit.html") or "").strip()
            case_path = Path(audit) if audit else None
            if case_path is not None and not case_path.is_absolute():
                case_path = path.parent / case_path
            case_dir = str(case_path.parent) if case_path is not None else ""
            out[t] = {
                "result": _to_int(r.get("Result")),
                "delegated": _to_int(r.get("Subagent-Delegate")) == 1,
                "cost": _to_float(r.get("total-Cost")),
                "case_dir": case_dir,
            }
    return out


def fill_one(
    mad_rows: dict[str, dict],
    sa_rows: dict[str, dict],
    out_dir: Path,
    label: str,
) -> tuple[int, int, int, int]:
    """Returns (n_success_pos, n_success_neg, n_failure_pos, n_failure_neg)."""
    buckets = {
        ("sub_success", "gt_0_5"): [],
        ("sub_success", "lt_0_5"): [],
        ("sub_failure", "gt_0_5"): [],
        ("sub_failure", "lt_0_5"): [],
    }
    for t, mr in mad_rows.items():
        if not mr["delegated"]:
            continue
        if t not in sa_rows:
            continue
        sr = sa_rows[t]
        sub = "sub_success" if mr["result"] == 1 else "sub_failure"
        # cost 是越低越好; u_c = sa/(mad+sa) > 0.5  ⟺  sa > mad
        posneg = "gt_0_5" if mr["cost"] < sr["cost"] else "lt_0_5"
        buckets[(sub, posneg)].append((t, mr["case_dir"]))

    counts = {}
    for (sub, posneg), entries in buckets.items():
        d = out_dir / sub / posneg / label
        d.mkdir(parents=True, exist_ok=True)
        entries.sort(key=lambda x: x[0])
        body = "".join(
            f"- [{t}](<{Path(os.path.relpath(cd, d)).as_posix()}>)\n" if cd else f"- {t}\n"
            for t, cd in entries
        )
        (d / "cases.md").write_text(body, encoding="utf-8")
        counts[(sub, posneg)] = len(entries)
    return (
        counts[("sub_success", "gt_0_5")],
        counts[("sub_success", "lt_0_5")],
        counts[("sub_failure", "gt_0_5")],
        counts[("sub_failure", "lt_0_5")],
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    print(f"{'experiment':46} {'sub_succ':>9} {'gt_0_5':>7} {'lt_0_5':>7} | {'sub_fail':>9} {'gt_0_5':>7} {'lt_0_5':>7}")
    for model, mode in EXPERIMENTS:
        label = f"{model}-{mode}"
        mad = load_summary(args.root / model / mode / "summary.csv")
        sa = load_summary(args.root / model / "single" / "summary.csv")
        if not mad or not sa:
            print(f"{label:46}  (missing MAD or SA summary.csv, skipped)")
            continue
        delegated = load_delegated_from_task_metrics(args.root / model / mode)
        for task, row in mad.items():
            row["delegated"] = delegated.get(task, False)
        ns_pos, ns_neg, nf_pos, nf_neg = fill_one(mad, sa, args.out, label)
        ns = ns_pos + ns_neg
        nf = nf_pos + nf_neg
        print(f"{label:46} {ns:>9} {ns_pos:>7} {ns_neg:>7} | {nf:>9} {nf_pos:>7} {nf_neg:>7}")


if __name__ == "__main__":
    main()
