#!/usr/bin/env python3
"""Parse delegation traces, construct function units, and compute hit scores.

Use eleven write labels (ten specific roles plus other-write) and fourteen
read-domain labels. Planning nodes are excluded. The matcher implements Eq. 2."""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from eval.delegation_appropriateness import guide_node_parser as parser

SCHEMA = "delegate-gt-tag-v3"
TAG_SOURCE = "oracle166-rule-expanded"
VOCAB_VERSION = "expanded-20260912-v2"

MATCHABLE_WRITE_ROLES = {
    "excel", "word", "ppt", "notion", "email", "calendar", "gsheet", "gform", "pdf",
    "processor",
}
WRITE_LABELS = MATCHABLE_WRITE_ROLES | {"other-write"}

DOMAINS = {
    "rail_12306", "woocommerce", "yahoo-finance", "snowflake", "scholarly-arxiv",
    "external-fetch", "notion", "youtube", "playwright-web", "filesystem-workspace",
    "canvas", "howtocook", "emails", "github",
}

HOWTOCOOK_RE = re.compile(
    r"(?i)\bhowtocook\b|\bmcp_howtocook\b|\bcatering\b|菜单|菜品|"
    r"\bcookbook\b|\brecipe\s+(catalog|database|explorer|owner|search|id)s?\b|"
    r"\bretrieve\b[^.]*\brecipes?\b|\brecipes?\s+from\b|"
    r"\bgetrecipes?\b|\bwhattoeat\b|\brecommendmeals\b"
)
SNOWFLAKE_RE = re.compile(
    r"(?i)\bsnowflake\b|\brun_query\b|\bdata warehouse\b|\.public\.|"
    r"\bsales_dw\b|\bwarehouse\b"
)
PDF_RE = re.compile(r"(?i)\.pdf\b|\bpdf\s+writer\b|\breportlab\b|\bcreate[_\s-]+pdf\b")

PLAN_TYPES = {"plan"}


def sha256_file(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, value) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)


def load_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def refine_domains(text: str, domains) -> list[str]:
    kept = set(domains or [])
    raw = text or ""
    if HOWTOCOOK_RE.search(raw):
        kept.add("howtocook")
    elif "howtocook" in kept:
        kept.discard("howtocook")
    if "snowflake" in kept and not SNOWFLAKE_RE.search(raw):
        kept.discard("snowflake")
    return sorted(kept & DOMAINS)


def refine_role(text: str, role: str | None) -> str:
    if role in MATCHABLE_WRITE_ROLES:
        return role
    if PDF_RE.search(text or ""):
        return "pdf"
    return "other-write"


def normalize_node(node: dict) -> dict:
    n = dict(node)
    if n.get("rw") == "write":
        n["role"] = refine_role(n.get("text", ""), n.get("role"))
        n["domains"] = []
    else:
        n["role"] = None
        n["domains"] = refine_domains(n.get("text", ""), n.get("domains"))
    n["is_plan"] = bool(n.get("is_plan"))
    return n


def clean_waves(waves: list[dict]) -> list[dict]:
    return [{**w, "nodes": [n for n in w["nodes"] if not n.get("is_plan")]}
            for w in waves if any(not n.get("is_plan") for n in w["nodes"])]


def parse_gt_waves(text: str) -> list[dict]:
    waves = []
    for wave in parser.parse_gt(text):
        nodes = [normalize_node(n) for n in wave.get("nodes") or []]
        waves.append({**wave, "nodes": nodes})
    return waves


def tagged_waves(raw_waves: list[dict], keep_plan: bool = False) -> list[dict]:
    waves = []
    node_id = 0
    for wave in raw_waves:
        nodes = []
        for node in wave.get("nodes") or []:
            node = normalize_node(node)
            nodes.append({
                "node_id": node_id,
                "wave_id": wave["wave_id"],
                "rw": node.get("rw"),
                "role": node.get("role"),
                "domains": list(node.get("domains") or []),
                "is_plan": bool(node.get("is_plan")),
                "declared": node.get("declared"),
                "text": node.get("text", ""),
                "domains_from": node.get("domains_from"),
                "n_agents": node.get("n_agents"),
                "tool": node.get("tool"),
                "profile": node.get("profile"),
                "resume": node.get("resume"),
                "call_id": node.get("call_id"),
                "raw_line": node.get("raw_line"),
            })
            node_id += 1
        waves.append({
            "wave_id": wave["wave_id"],
            "n_agents": wave.get("n_agents"),
            "n_agents_dynamic": bool(wave.get("n_agents_dynamic")),
            "nodes": nodes,
        })
    return waves if keep_plan else clean_waves(waves)


def actual_waves(raw) -> tuple[list[dict], dict]:
    waves = []
    plan = malformed = ignored_logs = runtime_logs = 0
    max_steps = False
    tool_counts = Counter()
    with Path(raw).open(encoding="utf-8", errors="strict") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            if re.match(r'^unknown format ".*" ignored in schema at path ', line):
                ignored_logs += 1
                continue
            # Harness trailers (max-steps, 402, empty reply). Prior Agent
            # calls stay in the file and still count for 踩点率.
            if line.startswith("error: failed to run prompt:"):
                runtime_logs += 1
                if "loop.max_steps_exceeded:" in line:
                    max_steps = True
                continue
            if line.startswith("See log: "):
                runtime_logs += 1
                continue
            try:
                obj = json.loads(line)
            except ValueError:
                malformed += 1
                continue
            if obj.get("role") != "assistant":
                continue
            nodes = []
            for call in obj.get("tool_calls") or []:
                fn = call.get("function") or {}
                name = fn.get("name", "").split(".")[-1]
                if name not in {"Agent", "AgentSwarm"}:
                    continue
                tool_counts[name] += 1
                try:
                    args = fn.get("arguments") or "{}"
                    if isinstance(args, str):
                        args = json.loads(args)
                    if not isinstance(args, dict):
                        raise ValueError("non-object arguments")
                except (ValueError, TypeError):
                    malformed += 1
                    continue
                template = args.get("prompt") or args.get("prompt_template") or ""
                items = args.get("items", args.get("tasks")) if name == "AgentSwarm" else None
                if isinstance(items, dict):
                    items = list(items.values())
                units = items if isinstance(items, list) else [None]
                profile = str(args.get("subagent_type") or args.get("profile") or "")
                for item in units:
                    assignment = str(template)
                    if item is not None:
                        item_text = item if isinstance(item, str) else json.dumps(item, ensure_ascii=False)
                        assignment = (
                            assignment.replace("{{item}}", item_text)
                            if "{{item}}" in assignment else assignment + "\n" + item_text
                        )
                    assignment += "\n" + str(args.get("description") or "")
                    node = normalize_node(parser.make_node(assignment.strip()))
                    node.update(
                        is_plan=profile.lower() in PLAN_TYPES,
                        call_id=call.get("id"),
                        tool=name,
                        raw_line=line_no,
                        resume=args.get("resume"),
                        profile=profile,
                    )
                    plan += int(node["is_plan"])
                    nodes.append(node)
            if nodes:
                waves.append({"wave_id": "message_" + str(line_no), "nodes": nodes})
    return waves, {
        "plan_nodes": plan,
        "malformed": malformed,
        "ignored_schema_warnings": ignored_logs,
        "runtime_log_lines": runtime_logs,
        "max_steps_termination": max_steps,
        "tool_counts": dict(tool_counts),
    }


def strict_units(waves: list[dict]) -> list[dict]:
    writes = []
    clusters = set()
    members = {}
    for wave in waves:
        for node in wave["nodes"]:
            if node["rw"] == "write":
                writes.append({
                    "id": f"write:{wave['wave_id']}:{node.get('node_id', len(writes))}:{node['role']}",
                    "kind": "write",
                    "wave": wave["wave_id"],
                    "node": node.get("node_id"),
                    "role": node["role"],
                    "matchable": node["role"] in MATCHABLE_WRITE_ROLES,
                })
            else:
                for domain in node.get("domains") or []:
                    key = (wave["wave_id"], domain)
                    clusters.add(key)
                    members.setdefault(key, []).append(node.get("node_id"))
    reads = [{
        "id": f"read:{wave_id}:{domain}",
        "kind": "read",
        "wave": wave_id,
        "domain": domain,
        "source_nodes": members[(wave_id, domain)],
        "matchable": True,
    } for wave_id, domain in sorted(clusters)]
    return writes + reads


def bag_counts(units: list[dict]) -> dict:
    writes = Counter(u["role"] for u in units if u["kind"] == "write" and u["matchable"])
    reads = Counter(u["domain"] for u in units if u["kind"] == "read")
    return {"write": dict(sorted(writes.items())), "read": dict(sorted(reads.items()))}


def matching(edges) -> list[list[int]]:
    matched = {}

    def augment(left, seen):
        for right in edges[left]:
            if right in seen:
                continue
            seen.add(right)
            if right not in matched or augment(matched[right], seen):
                matched[right] = left
                return True
        return False

    for left in range(len(edges)):
        augment(left, set())
    return sorted([[left, right] for right, left in matched.items()])


def prf(g, a, m):
    return {
        "gt_total": g,
        "actual_total": a,
        "matched": m,
        "recall": m / g if g else None,
        "precision": m / a if a else None,
        "f1": 2 * m / (g + a) if g + a else None,
    }


def compatible(g: dict, a: dict) -> bool:
    if g["kind"] != a["kind"]:
        return False
    if g["kind"] == "read":
        return g["domain"] == a["domain"]
    return g["role"] in MATCHABLE_WRITE_ROLES and g["role"] == a["role"]


def score_waves(gt_waves: list[dict], actual: list[dict]) -> dict:
    """Match reviewed sub-task units; other-write counts but cannot match."""
    gt = clean_waves(gt_waves)
    actual = clean_waves(actual)
    gu, au = strict_units(gt), strict_units(actual)
    pairs = matching([[j for j, a in enumerate(au) if compatible(g, a)] for g in gu])
    return {
        **prf(len(gu), len(au), len(pairs)),
        "pairs": pairs,
        "gt_units": gu,
        "actual_units": au,
    }


def load_gt_task(gt_path: Path, task: str) -> dict:
    path = Path(gt_path) / f"{task}.json"
    data = load_json(path)
    if data.get("schema") not in {SCHEMA, "delegate-gt-tag-v4", "delegate-gt-tag-v2", "delegate-gt-tag-v1"}:
        raise ValueError(f"unexpected schema in {path}: {data.get('schema')}")
    return data


def load_gt_index(gt_path: Path) -> dict:
    return load_json(Path(gt_path) / "_index.json")
