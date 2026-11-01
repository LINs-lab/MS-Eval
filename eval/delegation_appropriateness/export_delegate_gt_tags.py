#!/usr/bin/env python3
"""Regenerate golden tags from frozen nodes and cached v2 LLM review, offline.

Preserve the original node topology and task-level delegation decisions. Rebuild
all labels and derived fields from cached review; never reparse or call an API.
Source references are stored relative to the repository root.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from eval.common.paths import DEFAULT_CACHE, DEFAULT_GT, DEFAULT_ORACLE, portable_path
from eval.delegation_appropriateness.delegate_llm_review import load_task_text, review_sides
from eval.delegation_appropriateness.delegate_strict import (
    load_gt_index, load_gt_task, sha256_file, write_json,
)
from eval.delegation_appropriateness.reviewed_gt import (
    derived_fields, metadata, validate_reviewed_gt,
)


def export(oracle_dir: Path, out_dir: Path, gt_path: Path = DEFAULT_GT,
           cache: Path = DEFAULT_CACHE) -> dict:
    index = load_gt_index(gt_path)
    tasks = [row["task"] for row in index["tasks"]]
    oracle_tasks = {p.name[:-8] for p in oracle_dir.glob("*.task.md")}
    if len(tasks) != 166 or len(set(tasks)) != 166 or set(tasks) != oracle_tasks:
        raise ValueError("expected the same 166 tasks in GT and oracle166")
    records, jobs = [], []
    for task in tasks:
        seed = load_gt_task(gt_path, task)
        source = oracle_dir / f"{task}.task.md"
        if sha256_file(source) != seed["source"]["oracle166_sha256"]:
            raise ValueError(f"{task}: oracle166 hash mismatch")
        seed["source"]["oracle166"] = portable_path(source)
        records.append(seed)
        jobs.append(dict(side="gt", key="", task=task,
                         task_text=load_task_text(seed), waves=seed["waves"]))
    labels = review_sides(jobs, cache, allow_api=False)
    exported = []
    for seed in records:
        reviewed = labels[("gt", "", seed["task"])]
        waves = reviewed["waves"]
        record = {
            **metadata(),
            "task": seed["task"],
            "need_delegation": seed["need_delegation"],
            "source": seed["source"],
            "label_cache_keys": sorted(reviewed["cache_keys"]),
            "waves": waves,
            **derived_fields(waves),
        }
        validate_reviewed_gt(record)
        exported.append(record)
    index = {
        **metadata(),
        "oracle166": portable_path(oracle_dir),
        "n_tasks": len(exported),
        "n_need": sum(r["need_delegation"] for r in exported),
        "n_direct": sum(not r["need_delegation"] for r in exported),
        "n_units": sum(r["counts"]["units"] for r in exported),
        "n_nodes": sum(r["counts"]["nodes"] for r in exported),
        "tasks": [{"task": r["task"], "file": f"{r['task']}.json",
                   "need_delegation": r["need_delegation"], "counts": r["counts"],
                   "bag": r["bag"]} for r in exported],
    }
    if (index["n_need"], index["n_direct"]) != (89, 77):
        raise ValueError("expected 89 delegation-needed and 77 direct tasks")
    # Read and validate all inputs before writing, allowing in-place regeneration.
    out_dir.mkdir(parents=True, exist_ok=True)
    for record in exported:
        write_json(out_dir / f"{record['task']}.json", record)
    write_json(out_dir / "_index.json", index)
    return index


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--oracle", type=Path, default=DEFAULT_ORACLE)
    parser.add_argument("--gt-path", type=Path, default=DEFAULT_GT,
                        help="Existing golden nodes, either legacy seeds or reviewed GT")
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--out", type=Path, required=True,
                        help="Output directory; may equal --gt-path to update in place")
    args = parser.parse_args()
    index = export(args.oracle, args.out, args.gt_path, args.cache)
    print(f"wrote {index['n_tasks']} task files + _index.json → {args.out}\n"
          f"tags={index['tag_source']}  vocab={index['vocab']}  reviewer={index['reviewer']}\n"
          f"need_delegation={index['n_need']}  direct={index['n_direct']}  "
          f"nodes={index['n_nodes']}  units={index['n_units']}")


if __name__ == "__main__":
    main()
