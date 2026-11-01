#!/usr/bin/env python3
"""Recompute DA from local traces and compare six historical LLM hit columns."""
from __future__ import annotations

import argparse
import csv
from decimal import Decimal
import os
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from eval.common.paths import DEFAULT_CACHE, DEFAULT_GT, REPO_ROOT, portable_path
from eval.delegation_appropriateness.delegate_strict import sha256_file, write_json
from eval.delegation_appropriateness.evaluate import evaluate, write_csv

METRICS = ("gt_total", "actual_total", "matched", "recall", "precision", "f1")


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def table(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def task_map(rows: list[dict]) -> dict[str, dict]:
    result = {}
    for row in rows:
        task = (row.get("task") or row.get("Task") or "").strip()
        if not task or task in result:
            raise ValueError(f"missing or duplicate task ID: {task!r}")
        result[task] = row
    return result


def local_summary(source: Path, output: Path) -> None:
    """Keep selected task/slot suffixes, resolving them within the local dump."""
    rows = read_csv(source)
    task_map(rows)
    for row in rows:
        task = (row.get("task") or row.get("Task")).strip()
        raw = row.get("output_dir") or str(Path(row["audit.html"]).parent)
        parts = Path(raw).parts
        indices = [i for i, part in enumerate(parts) if part == task]
        if len(indices) != 1:
            raise ValueError(f"cannot identify task/slot suffix for {task}: {raw}")
        slot = source.parent.joinpath(*parts[indices[0]:]).resolve()
        if not slot.is_relative_to(source.parent.resolve()) or not slot.is_dir():
            raise ValueError(f"selected local slot missing or outside dump: {slot}")
        row["output_dir"] = Path(os.path.relpath(slot, output.parent)).as_posix()
        if "audit.html" in row:
            row["audit.html"] = Path(os.path.relpath(slot / "audit.html", output.parent)).as_posix()
    table(output, rows)


def compare(reference: list[dict], computed: list[dict]) -> list[dict]:
    old, new = task_map(reference), task_map(computed)
    if old.keys() != new.keys():
        raise ValueError(f"task sets differ: missing={sorted(old.keys()-new.keys())}, extra={sorted(new.keys()-old.keys())}")
    rows = []
    for task in sorted(old):
        for metric in METRICS:
            a, b = old[task][f"llm_strict_{metric}"], new[task][f"hit_{metric}"]
            # Undefined ratios are equal only when both recorded denominators
            # are zero. A missing numeric count must never count as a match.
            denominators = {"recall": ("gt_total",), "precision": ("actual_total",),
                            "f1": ("gt_total", "actual_total")}.get(metric, ())
            undefined = bool(denominators) and a == b == "" and all(
                row.get(prefix + key) not in (None, "") and Decimal(row[prefix + key]) == 0
                for row, prefix in ((old[task], "llm_strict_"), (new[task], "hit_"))
                for key in denominators
            )
            equal = undefined or (bool(a and b) and Decimal(a).is_finite()
                                  and Decimal(b).is_finite() and Decimal(a) == Decimal(b))
            rows.append(dict(task=task, metric=metric, reference=a, recomputed=b,
                             both_undefined=undefined, exact_match=equal))
    return rows


def run(results: Path, out: Path) -> dict:
    references = sorted(results.glob("*/*/task_metrics.csv"))
    if not references:
        raise ValueError(f"no historical task_metrics.csv found under {results}")
    if out.resolve().is_relative_to(results.resolve()) or results.resolve().is_relative_to(out.resolve()):
        raise ValueError("output and source directories must be separate")
    summaries = []
    for reference in references:
        dump = reference.parent
        model, variant = dump.relative_to(results).parts
        target = out / model / variant
        target.mkdir(parents=True, exist_ok=True)
        input_summary = target / "input_summary.csv"
        source_summary = dump / "summary.csv"
        hashes = {"reference_sha256": sha256_file(reference),
                  "source_summary_sha256": sha256_file(source_summary)}
        local_summary(source_summary, input_summary)
        report = evaluate(DEFAULT_GT, dump, summary=input_summary, cache=DEFAULT_CACHE)
        write_json(target / "summary.json", {k: v for k, v in report.items() if k != "rows"})
        write_json(target / "task_metrics.json", report["rows"])
        write_csv(target / "task_metrics.csv", report["rows"])
        comparisons = compare(read_csv(reference), read_csv(target / "task_metrics.csv"))
        table(target / "comparison.csv", comparisons)
        differences = [r for r in comparisons if not r["exact_match"]]
        unchanged = hashes == {"reference_sha256": sha256_file(reference),
                               "source_summary_sha256": sha256_file(source_summary)}
        score = report["hit_scores"]
        result = dict(model=model, variant=variant, tasks=report["n_gt_tasks"],
                      covered=report["n_covered"], compared_values=len(comparisons),
                      both_undefined=sum(r["both_undefined"] for r in comparisons),
                      mismatched_values=len(differences),
                      mismatched_tasks=len({r["task"] for r in differences}),
                      passed=not differences and unchanged and report["n_missing"] == 0,
                      **{f"hit_{metric}": score[metric] for metric in METRICS},
                      reference=portable_path(reference), output=portable_path(target),
                      source_summary=portable_path(source_summary), **hashes)
        summaries.append(result)
        print(f"{model}/{variant}: covered={result['covered']}/{result['tasks']}, "
              f"differences={len(differences)}/{len(comparisons)}", flush=True)
    table(out / "comparison_summary.csv", summaries)
    result = dict(schema="subagent-hit-regression-v1", comparison="exact decimal equality; zero-denominator undefined values must agree; no tolerance",
                  metric_mapping={f"llm_strict_{m}": f"hit_{m}" for m in METRICS},
                  n_experiments=len(summaries), n_tasks=sum(r["tasks"] for r in summaries),
                  n_compared_values=sum(r["compared_values"] for r in summaries),
                  n_both_undefined=sum(r["both_undefined"] for r in summaries),
                  n_mismatched_values=sum(r["mismatched_values"] for r in summaries),
                  passed=all(r["passed"] for r in summaries), experiments=summaries)
    write_json(out / "comparison_summary.json", result)
    lines = ["# Sub-agent Hit regression results", "",
             f"**{'PASS' if result['passed'] else 'FAIL'}**: {result['n_experiments']} experiments, "
             f"{result['n_tasks']:,} task rows, {result['n_compared_values']:,} compared values, "
             f"{result['n_mismatched_values']:,} differences.", "",
             "Each experiment was recomputed from its local `results/` traces with the current DA evaluator, reviewed GT, and cached runtime labels. No API calls were made. Task IDs are joined explicitly; duplicate IDs or unequal task sets fail verification. Numeric values must match exactly as decimal numbers, without rounding or tolerance. Two empty ratio cells match only when both corresponding denominators are zero: golden units for recall, executed units for precision, and their sum for F1. Empty counts, one-sided blanks, and nonfinite values do not pass.", "",
             f"There are {result['n_compared_values'] - result['n_both_undefined']:,} numeric comparisons and {result['n_both_undefined']:,} pairs of undefined ratios. Undefined values remain empty in CSV and null in JSON; they are not converted to zero.", "",
             "| Model | Variant | Covered tasks | Different values | Micro P | Micro R | Micro F1 |",
             "| --- | --- | ---: | ---: | ---: | ---: | ---: |"]
    for r in summaries:
        link = f"{r['model']}/{r['variant']}/task_metrics.csv"
        lines.append(f"| {r['model']} | [{r['variant']}]({link}) | {r['covered']}/{r['tasks']} | "
                     f"{r['mismatched_values']} | {r['hit_precision']:.8f} | {r['hit_recall']:.8f} | {r['hit_f1']:.8f} |")
    lines += ["", "## Column mapping", "", "| Historical CSV | Recomputed CSV |", "| --- | --- |"]
    lines += [f"| `llm_strict_{m}` | `hit_{m}` |" for m in METRICS]
    lines += ["", "## Reproduce", "", "Run from the repository root:", "", "```bash",
              "python3 -m eval.delegation_appropriateness.verify_results \\",
              "  --results results --out eval/eval_results", "```", "",
              "The command discovers model/variant directories containing historical `task_metrics.csv`. The duplicated auto-gen request is evaluated once. DeepSeek auto-spec uses its `summary.csv` for slot selection and its sibling `task_metrics.csv` for metric comparisons. The local `oracle` directory retains that name even though historical paths used `oracle-spec`.", "",
              "## Artifacts and paths", "",
              "Each model/variant directory contains `input_summary.csv` (the original selected task/slot suffixes rebased onto local traces), `summary.json` (DA aggregates), `task_metrics.csv` and `task_metrics.json` (recomputed task results), and `comparison.csv` (reference value, recomputed value, and equality for every task/metric). Input-summary paths are relative to that CSV; evaluator metadata paths are relative to the repository root. No original result files are modified.", "",
              "[comparison_summary.csv](comparison_summary.csv) and [comparison_summary.json](comparison_summary.json) record coverage, difference counts, and source CSV hashes for every experiment. Displayed aggregate scores are micro-averaged from total matched, golden, and executed units; they are not averages of per-task scores. The machine-readable artifacts retain full precision.", "",
              "This regression verifies the six LLM-reviewed Sub-agent Hit metrics. It neither computes nor compares rule-only or wide scores, and it does not establish correctness of OU or MSQ. Execution dumps in `results/` are required to reproduce the run and are not bundled with the evaluation materials."]
    # Keep the curated bilingual README separate from generated diagnostics.
    (out / "comparison_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=REPO_ROOT / "results")
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "eval/eval_results")
    args = parser.parse_args()
    result = run(args.results.resolve(), args.out.resolve())
    print(f"passed={result['passed']}; compared={result['n_compared_values']}; differences={result['n_mismatched_values']}")
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
