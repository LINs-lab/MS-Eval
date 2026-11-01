#!/usr/bin/env python3
"""Evaluate Delegation Appropriateness (UDR, ODR, and sub-agent hit scores).

Read frozen ground truth and the run slots selected by summary.csv. Exclude
planning-only sub-agents. By default, reuse LLM labels from the cache without
network calls; --match permits filling cache misses. Both golden and executed
nodes must pass LLM review before scoring. See this directory's README.md."""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from eval.common.paths import DEFAULT_CACHE, DEFAULT_GT, portable_path
from eval.delegation_appropriateness.delegate_llm_review import (
    PROMPT_VERSION, REVIEWER, load_task_text, review_sides,
)
from eval.delegation_appropriateness.delegate_strict import (
    DOMAINS, MATCHABLE_WRITE_ROLES, WRITE_LABELS, VOCAB_VERSION,
    actual_waves, bag_counts, clean_waves, load_gt_index,
    load_gt_task, prf, score_waves, sha256_file, tagged_waves, write_json,
)
from eval.delegation_appropriateness.rates import delegation_rates
from eval.delegation_appropriateness.reviewed_gt import REVIEWED_SCHEMA, validate_reviewed_gt

REPORT_SCHEMA = "delegation-appropriateness-v1"


def load_summary_slots(summary: Path) -> dict[str, Path]:
    """Task -> selected slot directory from summary.csv output_dir."""
    if not summary.is_file():
        raise SystemExit(f"missing summary.csv: {summary}")
    with summary.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise SystemExit(f"empty summary.csv: {summary}")
    fields = set(rows[0].keys())
    if "output_dir" not in fields and "audit.html" not in fields:
        raise SystemExit(f"{summary} has neither output_dir nor audit.html")
    mapping = {}
    for row in rows:
        task = (row.get("task") or row.get("Task") or "").strip()
        raw = (row.get("output_dir") or "").strip()
        if not raw:
            audit = (row.get("audit.html") or "").strip()
            raw = str(Path(audit).parent) if audit else ""
        if not task or not raw:
            continue
        slot = Path(raw)
        mapping[task] = slot if slot.is_absolute() else summary.parent / slot
    if not mapping:
        raise SystemExit(f"no task/output_dir rows in {summary}")
    return mapping


def raw_stream_in_slot(slot: Path) -> Path | None:
    if not slot.is_dir():
        return None
    hits = sorted(p for p in slot.rglob("raw_stream.jsonl") if p.is_file())
    if not hits:
        return None
    named = [p for p in hits if f"SingleUserTurn-{slot.parent.name}" in str(p)]
    chosen = named or hits
    if len(chosen) == 1:
        return chosen[0]
    return chosen[0]


def empty_row(gt: dict) -> dict:
    return {
        "task": gt["task"],
        "need_delegation": gt["need_delegation"],
        "gt_units": None,
        "gt_bag": None,
        "coverage": False,
        "coverage_reason": None,
        "output_dir": None,
        "scan": None,
        "raw_stream": None,
        "raw_sha256": None,
        "hit_scores": None,
        "actual_bag": None,
        "delegated": None,
        "plan_nodes_excluded": 0,
        "label_cache_keys": [],
    }


def score_pair(gt_waves, actual_waves) -> dict:
    scores = score_waves(gt_waves, actual_waves)
    cleaned = clean_waves(actual_waves)
    return {
        "hit_scores": scores,
        "gt_units": scores["gt_total"],
        "gt_bag": bag_counts(scores["gt_units"]),
        "actual_bag": bag_counts(scores["actual_units"]),
        "delegated": bool(cleaned),
    }


def parse_actual(raw: Path | None) -> tuple[list[dict] | None, dict, str | None]:
    """Parse raw_stream.jsonl. Malformed lines (API error truncation, partial
    writes) are tolerated: we keep whatever waves parsed cleanly so that
    API-Error runs still contribute GT units to the denominator. Only a
    completely missing/unreadable file is treated as uncovered."""
    if raw is None:
        return None, {}, "missing_raw_stream"
    try:
        waves, scan = actual_waves(raw)
    except OSError as exc:
        return None, {}, "unreadable_raw_stream:" + type(exc).__name__
    # malformed>0 is OK: bad lines are skipped by actual_waves, the rest counts.
    return waves, scan, None


def micro(rows: list[dict]) -> dict:
    covered = [r["hit_scores"] for r in rows if r["coverage"] and r["hit_scores"]]
    return prf(
        sum(r["gt_total"] for r in covered),
        sum(r["actual_total"] for r in covered),
        sum(r["matched"] for r in covered),
    )


def evaluate(
    gt_path: Path,
    dump: Path,
    summary: Path | None = None,
    match: bool = False,
    cache: Path | None = None,
    workers: int = 6,
    llm_key: Path | None = None,
) -> dict:
    index = load_gt_index(gt_path)
    summary_path = summary or (dump / "summary.csv")
    slots = load_summary_slots(summary_path)
    cache_dir = Path(cache or DEFAULT_CACHE)
    prepared = []
    for item in index["tasks"]:
        task = item["task"]
        gt = load_gt_task(gt_path, task)
        row = empty_row(gt)
        slot = slots.get(task)
        if slot is None:
            row["coverage_reason"] = "not_in_summary"
            prepared.append({"gt": gt, "actual": None, "row": row})
            continue
        row["output_dir"] = portable_path(slot)
        raw = raw_stream_in_slot(slot)
        actual, scan, reason = parse_actual(raw)
        if raw is not None:
            row["raw_stream"] = portable_path(raw)
            row["raw_sha256"] = sha256_file(raw)
        if actual is None:
            row["scan"] = scan or None
            if reason == "missing_raw_stream":
                row["coverage_reason"] = (
                    "missing_slot" if not slot.is_dir() else "missing_raw_stream"
                )
            else:
                row["coverage_reason"] = reason
            prepared.append({"gt": gt, "actual": None, "row": row})
            continue
        row.update(coverage=True, scan=scan, plan_nodes_excluded=scan["plan_nodes"])
        prepared.append({"gt": gt, "actual": actual, "row": row})

    jobs = []
    reviewed_gt = {}
    for item in prepared:
        gt = item["gt"]
        task = gt["task"]
        text = load_task_text(gt)
        if gt.get("schema") == REVIEWED_SCHEMA:
            validate_reviewed_gt(gt)
            reviewed_gt[("gt", "", task)] = {
                "waves": gt["waves"], "cache_keys": gt["label_cache_keys"],
            }
        else:
            jobs.append({
                "side": "gt",
                "key": "",
                "task": task,
                "task_text": text,
                "waves": gt["waves"],
            })
        if item["actual"] is not None:
            jobs.append({
                "side": "actual",
                "key": "dump",
                "task": task,
                "task_text": text,
                "waves": tagged_waves(item["actual"], keep_plan=True),
            })
    labels = review_sides(jobs, cache_dir, allow_api=match, workers=workers, key_path=llm_key)
    labels.update(reviewed_gt)

    rows = []
    for item in prepared:
        row = item["row"]
        gt = item["gt"]
        if item["actual"] is not None:
            gt_llm = labels[("gt", "", gt["task"])]
            act_llm = labels[("actual", "dump", gt["task"])]
            row.update(score_pair(gt_llm["waves"], act_llm["waves"]))
            row["plan_nodes_excluded"] = sum(
                1 for wave in act_llm["waves"] for node in wave["nodes"] if node.get("is_plan")
            )
            row["label_cache_keys"] = gt_llm["cache_keys"] + act_llm["cache_keys"]
        rows.append(row)

    covered = [r for r in rows if r["coverage"]]
    return {
        "schema": REPORT_SCHEMA,
        "gt_input_schema": index.get("schema"),
        "vocab": VOCAB_VERSION,
        "prompt_version": PROMPT_VERSION,
        "label_source": "llm",
        "reviewer": REVIEWER,
        "function_labels": {
            "write": sorted(WRITE_LABELS),
            "read": sorted(DOMAINS),
            "matchable_write": sorted(MATCHABLE_WRITE_ROLES),
        },
        "gt_path": portable_path(gt_path),
        "dump": portable_path(dump),
        "summary": portable_path(summary_path),
        "cache": portable_path(cache_dir),
        "gt_input_vocab": index.get("vocab"),
        "delegation_rates": delegation_rates(
            {r["task"]: r["need_delegation"] for r in rows},
            {r["task"]: r["delegated"] for r in covered},
        ),
        "n_gt_tasks": len(rows),
        "n_covered": len(covered),
        "n_missing": sum(not r["coverage"] for r in rows),
        "n_need": sum(r["need_delegation"] for r in rows),
        "n_delegated": sum(r["delegated"] is True for r in rows),
        "plan_nodes_excluded": sum(r["plan_nodes_excluded"] for r in rows),
        "hit_scores": micro(rows),
        "missing_tasks": [r["task"] for r in rows if not r["coverage"]],
        "rows": rows,
    }


def flatten(row: dict) -> dict:
    out = {
        "task": row["task"],
        "need_delegation": row["need_delegation"],
        "covered": row["coverage"],
        "coverage_reason": row["coverage_reason"],
        "delegated": row["delegated"],
        "plan_nodes_excluded": row["plan_nodes_excluded"],
        "output_dir": row.get("output_dir"),
        "raw_stream": row["raw_stream"],
    }
    score = row.get("hit_scores") or {}
    for key in ("gt_total", "actual_total", "matched", "precision", "recall", "f1"):
        out[f"hit_{key}"] = score.get(key)
    return out


def write_csv(path: Path, rows: list[dict]) -> None:
    import csv
    flat = [flatten(r) for r in rows]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(flat[0].keys()) if flat else [])
        writer.writeheader()
        writer.writerows(flat)


def fmt(value, pct=False) -> str:
    if value is None:
        return "—"
    return f"{value * 100:.2f}%" if pct else f"{value:.4f}"


def fmt_prf(score: dict) -> str:
    return (
        f"{fmt(score.get('precision'), True)} / "
        f"{fmt(score.get('recall'), True)} / "
        f"{fmt(score.get('f1'), True)}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gt_path", "--gt-path", dest="gt_path", type=Path, default=DEFAULT_GT,
                        help="Frozen GT directory (default: bundled DA annotations)")
    parser.add_argument("--dump", type=Path, required=True,
                        help="Experiment directory containing summary.csv and execution traces")
    parser.add_argument("--summary", type=Path, default=None,
                        help="Slot-selection CSV (default: <dump>/summary.csv)")
    parser.add_argument("--out", type=Path, required=True,
                        help="Output directory for summary.json and task_metrics.{json,csv}")
    parser.add_argument("--match", action="store_true",
                        help="Allow API calls to fill missing LLM label chunks")
    parser.add_argument("--cache", type=Path, default=None,
                        help="LLM label cache (default: bundled DA cache)")
    parser.add_argument("--workers", type=int, default=6,
                        help="Concurrent labeling workers (default: 6)")
    parser.add_argument("--llm-key", type=Path, default=None,
                        help="API key file (alternative: DELEGATE_LLM_API_KEY environment variable)")
    args = parser.parse_args()
    report = evaluate(
        args.gt_path, args.dump, args.summary,
        match=args.match,
        cache=args.cache, workers=args.workers, llm_key=args.llm_key,
    )
    args.out.mkdir(parents=True, exist_ok=True)
    write_json(args.out / "summary.json", {k: v for k, v in report.items() if k != "rows"})
    write_json(args.out / "task_metrics.json", report["rows"])
    write_csv(args.out / "task_metrics.csv", report["rows"])
    print(
        f"dump={args.dump}\n"
        f"summary={report['summary']}\n"
        f"gt_path={args.gt_path}\n"
        f"covered={report['n_covered']}/{report['n_gt_tasks']}  "
        f"missing={report['n_missing']}  label_source={report['label_source']}\n"
        f"UDR={fmt(report['delegation_rates']['udr'], True)}  "
        f"ODR={fmt(report['delegation_rates']['odr'], True)}\n"
        f"Sub-agent hit P/R/F1 = {fmt_prf(report['hit_scores'])}\n"
        f"wrote {args.out / 'summary.json'}"
    )


if __name__ == "__main__":
    main()
