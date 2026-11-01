"""Build and validate materialized LLM-reviewed golden annotations."""
from __future__ import annotations

from eval.common.paths import repository_path
from eval.delegation_appropriateness.delegate_llm_review import (
    PROMPT_VERSION, REVIEWER, SYSTEM, _jobs_for, load_task_text, stable_hash,
)
from eval.delegation_appropriateness.delegate_strict import (
    DOMAINS, MATCHABLE_WRITE_ROLES, WRITE_LABELS, VOCAB_VERSION,
    bag_counts, clean_waves, sha256_file, strict_units,
)

REVIEWED_SCHEMA = "delegate-gt-tag-v4"


def metadata() -> dict:
    return {
        "schema": REVIEWED_SCHEMA,
        "vocab": VOCAB_VERSION,
        "tag_source": "llm",
        "reviewer": REVIEWER,
        "prompt_version": PROMPT_VERSION,
        "system_sha256": stable_hash(SYSTEM),
        "roles": sorted(WRITE_LABELS),
        "write_labels": sorted(WRITE_LABELS),
        "matchable_roles": sorted(MATCHABLE_WRITE_ROLES),
        "domains": sorted(DOMAINS),
    }


def derived_fields(waves: list[dict]) -> dict:
    nodes = [node for wave in waves for node in wave["nodes"]]
    units = strict_units(clean_waves(waves))
    return {
        "nodes": nodes,
        "units": units,
        "bag": bag_counts(units),
        "counts": {
            "waves": len(waves),
            "nodes": len(nodes),
            "units": len(units),
            "write_units": sum(u["kind"] == "write" for u in units),
            "read_clusters": sum(u["kind"] == "read" for u in units),
            "other_write": sum(u["kind"] == "write" and not u["matchable"] for u in units),
            "unlabeled_read_nodes": sum(n["rw"] == "read" and not n["domains"] for n in nodes),
        },
    }


def validate_reviewed_gt(record: dict) -> None:
    """Reject stale protocol, source, node labels, or derived statistics."""
    task = record["task"]
    for key, expected in metadata().items():
        if record.get(key) != expected:
            raise ValueError(f"{task}: reviewed GT {key} mismatch; use matching GT and labeling protocol")
    source = record["source"]
    if sha256_file(repository_path(source["oracle166"])) != source["oracle166_sha256"]:
        raise ValueError(f"{task}: oracle166 hash mismatch")
    for wave in record["waves"]:
        for node in wave["nodes"]:
            valid = (
                node.get("tag_source") == "llm"
                and type(node.get("is_plan")) is bool
                and set(node.get("domains", [])) <= DOMAINS
                and ((node.get("rw") == "write" and node.get("role") in WRITE_LABELS
                      and node.get("domains") == [])
                     or (node.get("rw") == "read" and node.get("role") is None))
            )
            if not valid:
                raise ValueError(f"{task}: invalid reviewed node label")
    keys = sorted(job[3] for job in _jobs_for("gt", "", task, load_task_text(record), record["waves"]))
    if record.get("label_cache_keys") != keys:
        raise ValueError(f"{task}: reviewed GT cache provenance mismatch")
    for key, expected in derived_fields(record["waves"]).items():
        if record.get(key) != expected:
            raise ValueError(f"{task}: reviewed GT {key} mismatch")
