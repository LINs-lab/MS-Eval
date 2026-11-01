"""Offline integrity and regression checks for the public evaluation workflow."""
from __future__ import annotations

import csv
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from eval.common.paths import DATA_DIR, DEFAULT_CACHE, DEFAULT_GT, REPO_ROOT, TASK_CATEGORIES_DIR
from eval.common.build_audit_summary import (
    expand_dump_roots, find_audit_htmls, infer_model_key, rates_for,
)
from eval.delegation_appropriateness.delegate_llm_review import (
    PROMPT_VERSION, REVIEWER, SYSTEM, _jobs_for, load_task_text, review_sides, stable_hash,
)
from eval.delegation_appropriateness.delegate_strict import (
    DOMAINS, MATCHABLE_WRITE_ROLES, WRITE_LABELS, actual_waves, clean_waves,
    matching, score_waves, strict_units, tagged_waves,
)
from eval.delegation_appropriateness.rates import delegation_rates
from eval.delegation_appropriateness.reviewed_gt import validate_reviewed_gt
from eval.delegation_appropriateness.evaluate import evaluate
from eval.delegation_appropriateness.verify_results import METRICS, compare, local_summary
from eval.orchestration_utilities.metrics import TaskRow, utilities
from eval.summarize import load_hit_prf


class DataIntegrityTests(unittest.TestCase):
    def test_reviewed_gt_integrity_and_protocol_rejection(self):
        index = json.loads((DEFAULT_GT / "_index.json").read_text())
        self.assertEqual(index["schema"], "delegate-gt-tag-v4")
        self.assertEqual(set(index["roles"]), WRITE_LABELS)
        self.assertEqual(set(index["matchable_roles"]), MATCHABLE_WRITE_ROLES)
        self.assertEqual((index["n_nodes"], index["n_units"]), (556, 265))
        processor = 0
        for item in index["tasks"]:
            record = json.loads((DEFAULT_GT / item["file"]).read_text())
            validate_reviewed_gt(record)
            self.assertEqual(record["counts"], item["counts"])
            self.assertEqual(record["bag"], item["bag"])
            processor += sum(u.get("role") == "processor" for u in record["units"])
        self.assertEqual(processor, 7)
        record = json.loads((DEFAULT_GT / "academic-literature-review.json").read_text())
        for field, value in (("reviewer", "different-model"), ("label_cache_keys", []),
                             ("counts", {}), ("roles", ["excel"])):
            broken = copy.deepcopy(record)
            broken[field] = value
            with self.assertRaisesRegex(ValueError, "mismatch"):
                validate_reviewed_gt(broken)

    def test_task_sources_partitions_and_hashes(self):
        index = json.loads((DEFAULT_GT / "_index.json").read_text())
        self.assertEqual(index["oracle166"], "data/oracle166")
        self.assertEqual((index["n_tasks"], index["n_need"], index["n_direct"]), (166, 89, 77))
        tasks = {item["task"] for item in index["tasks"]}
        self.assertEqual(tasks, {p.name[:-8] for p in (DATA_DIR / "oracle166").glob("*.task.md")})
        for task in tasks:
            record = json.loads((DEFAULT_GT / f"{task}.json").read_text())
            source = record["source"]
            self.assertEqual(source["oracle166"], f"data/oracle166/{task}.task.md")
            self.assertEqual(hashlib.sha256((REPO_ROOT / source["oracle166"]).read_bytes()).hexdigest(),
                             source["oracle166_sha256"])
        categories = TASK_CATEGORIES_DIR / "cluster_by_delegation"
        need = set((categories / "need_subagent/need_subagent.txt").read_text().split())
        no_need = set((categories / "no_need_subagent/no_need_subagent.txt").read_text().split())
        self.assertFalse(need & no_need)
        self.assertEqual(need | no_need, tasks)
        self.assertEqual(need, {item["task"] for item in index["tasks"] if item["need_delegation"]})
        slices = [set((categories / f"need_subagent/{name}/{name}.txt").read_text().split())
                  for name in ("read_only", "writable", "read_and_write")]
        self.assertEqual([len(group) for group in slices], [22, 23, 44])
        self.assertEqual(set.union(*slices), need)
        with (TASK_CATEGORIES_DIR / "cluster_by_domain/domain-cases.tsv").open() as handle:
            domain_rows = list(csv.DictReader(handle, delimiter="\t"))
        self.assertEqual(len(domain_rows), 166)
        self.assertEqual({row["case_name"] for row in domain_rows}, tasks)

    def test_cache_hashes_and_offline_gt_reuse_from_other_directory(self):
        for path in DEFAULT_CACHE.glob("*.json"):
            entry = json.loads(path.read_text())
            self.assertEqual(entry["input_hash"], path.stem)
        with tempfile.TemporaryDirectory() as directory:
            previous = Path.cwd()
            try:
                os.chdir(directory)
                items = []
                for path in DEFAULT_GT.glob("*.json"):
                    if path.name == "_index.json":
                        continue
                    gt = json.loads(path.read_text())
                    items.append(dict(side="gt", key="", task=gt["task"],
                                      task_text=load_task_text(gt), waves=gt["waves"]))
                with patch("urllib.request.urlopen", side_effect=AssertionError("Unexpected API call")):
                    labels = review_sides(items, DEFAULT_CACHE, allow_api=False)
                self.assertEqual(len(labels), 166)
                self.assertEqual(sum(len(item["cache_keys"]) for item in labels.values()), 101)
                units = [unit for item in labels.values() for unit in strict_units(clean_waves(item["waves"]))]
                self.assertEqual(len(units), 265)
                self.assertEqual(sum(unit.get("role") == "processor" for unit in units), 7)
                self.assertFalse(any(unit.get("role") == "other-write" for unit in units))
            finally:
                os.chdir(previous)

    def test_readme_links(self):
        for root in (DATA_DIR, REPO_ROOT / "eval"):
            for path in root.rglob("README.md"):
                for target in re.findall(r"\]\(([^)]+)\)", path.read_text()):
                    target = target.split("#", 1)[0].strip("<>")
                    if target and "://" not in target:
                        self.assertTrue((path.parent / target).exists(), f"{path}: {target}")


class MetricTests(unittest.TestCase):
    def test_rates_exclude_unknown_decisions(self):
        rates = delegation_rates({"miss": True, "hit": True, "over": False, "unknown": False},
                                 {"miss": False, "hit": True, "over": True})
        self.assertEqual((rates["udr"], rates["odr"], rates["n_missing"]), (0.5, 1.0, 1))

    def test_maximum_matching_and_wave_local_read_units(self):
        self.assertEqual(len(matching([[0, 1], [0]])), 2)
        read = {"rw": "read", "role": None, "domains": ["canvas"], "is_plan": False}
        gold = [{"wave_id": "g1", "nodes": [dict(read), dict(read)]},
                {"wave_id": "g2", "nodes": [dict(read)]}]
        actual = [{"wave_id": "a1", "nodes": [dict(read), dict(read, is_plan=True)]}]
        with patch("eval.delegation_appropriateness.delegate_strict.matching", wraps=matching) as match:
            hit = score_waves(gold, actual)
        self.assertEqual(match.call_count, 1)
        self.assertEqual((hit["gt_total"], hit["actual_total"], hit["matched"]), (2, 1, 1))
        self.assertEqual((hit["precision"], hit["recall"]), (1.0, 0.5))

    def test_write_vocabulary_includes_fallback_without_matching_it(self):
        self.assertEqual(len(DOMAINS), 14)
        self.assertEqual(len(WRITE_LABELS), 11)
        self.assertEqual(len(MATCHABLE_WRITE_ROLES), 10)
        nodes = [{"rw": "write", "role": role, "domains": [], "is_plan": False}
                 for role in ("processor", "other-write")]
        waves = [{"wave_id": "w1", "nodes": nodes}]
        hit = score_waves(waves, waves)
        self.assertEqual((hit["gt_total"], hit["actual_total"], hit["matched"]), (2, 2, 1))
        self.assertEqual((hit["precision"], hit["recall"], hit["f1"]), (0.5, 0.5, 0.5))

    def test_missing_review_cache_never_falls_back_to_seed_labels(self):
        item = dict(side="actual", key="dump", task="example", task_text="Example",
                    waves=[{"wave_id": "w1", "nodes": [{"text": "Write an Excel file"}]}])
        with tempfile.TemporaryDirectory() as directory:
            with patch("urllib.request.urlopen", side_effect=AssertionError("Unexpected API call")):
                with self.assertRaisesRegex(RuntimeError, "LLM review is required"):
                    review_sides([item], Path(directory), allow_api=False)

    def test_combined_report_reads_reviewed_scores_in_both_formats(self):
        hit = {"precision": 0.5, "recall": 0.75, "f1": 0.6}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "summary.json"
            for report in ({"label_source": "llm", "hit_scores": hit},
                           {"primary": "llm", "llm": {"strict": hit}}):
                path.write_text(json.dumps(report))
                self.assertEqual(load_hit_prf(root), (0.5, 0.75, 0.6))
            path.write_text(json.dumps({"primary": "rule", "strict": hit, "llm": None}))
            self.assertEqual(load_hit_prf(root), (None, None, None))

    def test_utilities_use_mad_success_and_exclude_planning_and_unknown(self):
        mad = {
            "solved": TaskRow("solved", 1, 4, True, 2),
            "failed": TaskRow("failed", 0, 100, True, 100),
            "plan": TaskRow("plan", 1, 999, True, 999),
            "unknown": TaskRow("unknown", 1, 999, True, 999),
        }
        sa = {
            "solved": TaskRow("solved", 0, 12, False, 6),
            "failed": TaskRow("failed", 1, 20, False, 20),
            "plan": TaskRow("plan", 1, 1, False, 1),
            "unknown": TaskRow("unknown", 1, 1, False, 1),
        }
        decisions = {"solved": True, "failed": True, "plan": False}
        result = utilities(mad, sa, delegated_map=decisions)
        self.assertEqual((result["n_dsub"], result["n_pool"]), (2, 1))
        self.assertEqual((result["U_p"], result["U_e"], result["U_c"]), (0.5, 0.75, 0.75))
        self.assertEqual(utilities(mad, sa, True, decisions)["n_pool"], 2)
        self.assertIsNone(utilities(mad, sa, delegated_map={}))
        zero = {"z": TaskRow("z", 1, 0, True, 0)}
        self.assertIsNone(utilities(zero, zero, delegated_map={"z": True})["U_c"])

    def test_recorded_price_tier_boundaries(self):
        self.assertEqual(rates_for("minimax-m3", 512000), (0.31, 0.06, 1.25))
        self.assertEqual(rates_for("minimax-m3", 512001), (0.63, 0.13, 2.5))
        self.assertEqual(rates_for("gpt-5.6-sol", 272000), (4.0, 0.4, 20.0))
        self.assertEqual(rates_for("gpt-5.6-sol", 272001), (8.0, 0.8, 30.0))

    def test_launcher_batches_merge_latest_attempt_and_skip_smoke(self):
        with tempfile.TemporaryDirectory() as directory:
            results = Path(directory) / "results"
            spec = results / "kimi-k3/spec"
            for run_id, tasks, plan in (("20261030-090000-aaaaaa", ("t1", "t2"), {}),
                                        ("20261031-090000-bbbbbb", ("t1",), {}),
                                        ("20261101-090000-cccccc", ("t2",), {"smoke": True})):
                (spec / run_id).mkdir(parents=True)
                (spec / run_id / "run.json").write_text(json.dumps(plan))
                for task in tasks:
                    slot = spec / run_id / task / f"{run_id}_slot0"
                    slot.mkdir(parents=True)
                    (slot / "audit.html").write_text("<main></main>")
            found = {task: path.parent.name for task, path in find_audit_htmls(spec)}
            self.assertEqual(found, {"t1": "20261031-090000-bbbbbb_slot0",
                                     "t2": "20261030-090000-aaaaaa_slot0"})
            self.assertEqual(expand_dump_roots([results]), [spec])
            self.assertEqual(infer_model_key(spec), "kimi-k3")
            self.assertEqual(infer_model_key(spec / "20261030-090000-aaaaaa"), "kimi-k3")
            self.assertIsNone(infer_model_key(results / "unknown-model/spec"))


class WorkflowTests(unittest.TestCase):
    def test_historical_comparison_matches_by_task_and_rejects_missing_values(self):
        old = [dict(task=task, **{f"llm_strict_{m}": "1" for m in METRICS})
               for task in ("a", "b")]
        new = [dict(task=task, **{f"hit_{m}": "1.0" for m in METRICS})
               for task in ("b", "a")]
        self.assertTrue(all(row["exact_match"] for row in compare(old, new)))
        new[0]["hit_f1"] = "0.9999999999999999"
        self.assertEqual(sum(not row["exact_match"] for row in compare(old, new)), 1)
        for value in ("", "NaN", "Infinity"):
            old[0]["llm_strict_f1"] = value
            new[1]["hit_f1"] = value
            self.assertEqual(sum(not row["exact_match"] for row in compare(old, new)), 2)
        old[0].update({f"llm_strict_{m}": "0" for m in ("gt_total", "actual_total", "matched")})
        new[1].update({f"hit_{m}": "0" for m in ("gt_total", "actual_total", "matched")})
        for metric in ("recall", "precision", "f1"):
            old[0][f"llm_strict_{metric}"] = ""
            new[1][f"hit_{metric}"] = ""
        compared = compare(old, new)
        self.assertEqual(sum(row["both_undefined"] for row in compared), 3)
        self.assertEqual(sum(not row["exact_match"] for row in compared), 1)
        new[1]["hit_recall"] = "0"
        self.assertEqual(sum(not row["exact_match"] for row in compare(old, new)), 2)
        with self.assertRaisesRegex(ValueError, "task sets differ"):
            compare(old, new[:1])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            compare(old + old[:1], new)

    def test_historical_slot_rebase_uses_local_task_and_slot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dump = root / "results/model/oracle"
            slot = dump / "task-a/selected-slot"
            slot.mkdir(parents=True)
            source = dump / "summary.csv"
            source.write_text("Task,audit.html\ntask-a,/old/repo/model/oracle-spec/task-a/selected-slot/audit.html\n")
            before = source.read_bytes()
            output = root / "eval_results/model/oracle/input_summary.csv"
            local_summary(source, output)
            with output.open() as handle:
                row = next(csv.DictReader(handle))
            self.assertFalse(Path(row["output_dir"]).is_absolute())
            self.assertEqual((output.parent / row["output_dir"]).resolve(), slot)
            self.assertEqual(source.read_bytes(), before)

    def run_cli(self, script, *args, cwd):
        result = subprocess.run([sys.executable, str(REPO_ROOT / script), *map(str, args)],
                                cwd=cwd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def test_summary_da_ou_and_combined_report_from_outside_checkout(self):
        self.check_workflow("auto-spec", "single", batch="")

    def test_workflow_reads_launcher_output_directly(self):
        self.check_workflow("spec", "sa", batch="20261015-120000-abc123")

    def check_workflow(self, mad_name, sa_name, batch):
        with tempfile.TemporaryDirectory(prefix="ms eval test ") as directory:
            root = Path(directory)
            runs = root / "runs"
            mad = runs / "deepseek-v4-flash-0731" / mad_name
            sa = mad.parent / sa_name
            task = "arxiv-lit-review-gsheet"
            slot_name = f"{batch or '20261015-120000'}_slot0"
            for dump in (mad, sa):
                slot = dump / batch / task / slot_name
                slot.mkdir(parents=True)
                (slot / "audit.html").write_text('<main><section id="summary"></section></main>')
                # A planning-only invocation must never enter D_del.
                event = {"role": "assistant", "tool_calls": [{"function": {
                    "name": "Agent", "arguments": json.dumps({"subagent_type": "plan", "prompt": "Plan the task"})}}]}
                (slot / "raw_stream.jsonl").write_text(json.dumps(event) + "\n")
            # A cached reviewed planning node makes this CLI test fully offline.
            gt_path = root / "gt"
            gt_path.mkdir()
            gt = json.loads((DEFAULT_GT / f"{task}.json").read_text())
            self.assertEqual(gt["waves"], [])
            shutil.copy2(DEFAULT_GT / f"{task}.json", gt_path / f"{task}.json")
            (gt_path / "_index.json").write_text(json.dumps({
                "schema": gt["schema"], "vocab": gt["vocab"],
                "tasks": [{"task": task, "need_delegation": False}],
            }))
            cache = root / "cache"
            cache.mkdir()
            actual, _ = actual_waves(mad / batch / task / slot_name / "raw_stream.jsonl")
            jobs = _jobs_for("actual", "dump", task, load_task_text(gt), tagged_waves(actual, keep_plan=True))
            for _, _, _, digest, payload in jobs:
                (cache / f"{digest}.json").write_text(json.dumps({
                    "input_hash": digest, "reviewer": REVIEWER, "prompt_version": PROMPT_VERSION,
                    "system_sha256": stable_hash(SYSTEM), "payload": payload,
                    "result": {"tags": [{"id": node["id"], "rw": "read", "role": None,
                                         "domains": [], "is_plan": True} for node in payload["nodes"]]},
                }))
            self.run_cli("eval/common/build_audit_summary.py", mad, sa, cwd=root)
            with (mad / "summary.csv").open() as handle:
                row = next(csv.DictReader(handle))
            self.assertFalse(Path(row["audit.html"]).is_absolute())
            self.assertTrue((mad / row["audit.html"]).is_file())
            output = self.run_cli("eval/delegation_appropriateness/evaluate.py",
                                  "--dump", mad, "--out", mad, "--gt-path", gt_path, "--cache", cache, cwd=root)
            self.assertIn("Sub-agent hit P/R/F1", output)
            self.assertNotIn("wide", output)
            self.assertNotIn("rule", output)
            summary = json.loads((mad / "summary.json").read_text())
            self.assertEqual(summary["label_source"], "llm")
            self.assertEqual(len(summary["function_labels"]["write"]), 11)
            self.assertEqual(summary["gt_input_vocab"], "expanded-20260912-v2")
            self.assertEqual(summary["vocab"], "expanded-20260912-v2")
            for value in [summary, *json.loads((mad / "task_metrics.json").read_text())]:
                self.assertFalse({"wide", "strict", "rule", "llm"} & value.keys())
            with (mad / "task_metrics.csv").open() as handle:
                fields = next(csv.reader(handle))
            self.assertIn("hit_f1", fields)
            self.assertFalse(any("wide" in key or "rule" in key for key in fields))
            self.assertEqual((summary["n_covered"], summary["n_delegated"]), (1, 0))
            self.assertEqual(summary["plan_nodes_excluded"], 1)
            self.assertEqual(summary["delegation_rates"]["odr"], 0)
            result = json.loads(self.run_cli("eval/orchestration_utilities/evaluate.py",
                                            "--mad", mad, "--sa", sa, cwd=root))
            self.assertIsNone(result["utilities"])
            table = self.run_cli("eval/summarize.py", "--root", runs, cwd=root)
            self.assertIn(f"deepseek-v4-flash-0731/{mad_name}", table)
            self.assertNotIn(f"deepseek-v4-flash-0731/{sa_name}", table)
            self.assertIn("0.0% (0/1)", table)

    def test_gt_export_records_relative_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "generated"
            self.run_cli("eval/delegation_appropriateness/export_delegate_gt_tags.py",
                         "--out", out, cwd=directory)
            index = json.loads((out / "_index.json").read_text())
            self.assertEqual(index["oracle166"], "data/oracle166")
            self.assertEqual(index["vocab"], "expanded-20260912-v2")
            self.assertEqual(index["n_tasks"], 166)
            self.assertEqual(set(index["write_labels"]), WRITE_LABELS)
            self.assertEqual(set(index["roles"]), WRITE_LABELS)
            for path in out.glob("*.json"):
                self.assertEqual(path.read_bytes(), (DEFAULT_GT / path.name).read_bytes())
            # In-place export must also be deterministic.
            self.run_cli("eval/delegation_appropriateness/export_delegate_gt_tags.py",
                         "--gt-path", out, "--out", out, cwd=directory)
            for path in out.glob("*.json"):
                self.assertEqual(path.read_bytes(), (DEFAULT_GT / path.name).read_bytes())

    def test_reviewed_gt_needs_no_golden_cache_or_second_review(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            slot = root / "slot"
            slot.mkdir()
            (slot / "raw_stream.jsonl").write_text("")
            (root / "summary.csv").write_text(
                "task,output_dir\nacademic-literature-review,slot\n")
            seen = []
            def review_actual_only(items, *args, **kwargs):
                seen.extend(items)
                self.assertTrue(all(item["side"] == "actual" for item in items))
                return review_sides(items, *args, **kwargs)
            with patch("eval.delegation_appropriateness.evaluate.review_sides", review_actual_only):
                report = evaluate(DEFAULT_GT, root, cache=root / "empty-cache")
            self.assertEqual(len(seen), 1)
            self.assertEqual(report["n_covered"], 1)
            self.assertGreater(report["hit_scores"]["gt_total"], 0)
            self.assertEqual(report["hit_scores"]["actual_total"], 0)


if __name__ == "__main__":
    unittest.main()
