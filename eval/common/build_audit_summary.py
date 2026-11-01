#!/usr/bin/env python3
"""Build a per-task summary.csv from audit.html pages plus wire.jsonl usage.

Columns:

  Task
  Result                         Eval pill: PASS -> 1, otherwise 0
  Comment                        stop reason. Top-tier (same priority group;
                                   if several match: timeout > 403_auth >
                                   same_tool_loop > job_teardown):
                                   timeout | 403_auth | same_tool_loop |
                                   job_teardown
                                 Then, only if none of those apply:
                                   preprocess_failed |
                                   filtered |
                                   case_summary_missing |
                                   api_error_cause_100_step_limit | 100_step_limit |
                                   API Error |
                                   terminate_with_text |
                                   claim_done | no_claim_done | ...
  Critical Steps                 already excludes API-error steps
  Subagent-Delegate              1 if any sub-agent run exists, else 0
  Duration                       same string as the audit.html Duration field
  API Error Steps(main-agent/subagent)
                                 main-agent count / sub-agent count
  Checkpoints                    same string as the audit.html Checkpoints field
  inputOther                     uncached input tokens
  inputCacheRead                 cache-hit input tokens
  inputCacheCreation             cache-write input tokens
  output                         model output tokens
  Input-Cost                     USD for inputOther (cache-miss rate)
  inputCacheRead-Cost            USD for inputCacheRead (cache-hit rate)
  output-Cost                    USD for output tokens
  total-Cost                     sum of the three USD columns
  audit.html                     path relative to the output CSV directory

Prices are USD per 1M tokens. MiniMax-M3 and GPT-5.6-Sol use a higher
rate when that request's input tokens (other + cache-read + cache-write)
exceed 512K / 272K respectively. inputCacheCreation is counted in the
tier threshold but is not billed in these four columns.

Eval / steps / duration / checkpoints are parsed from audit.html so they stay
aligned with the page. Token columns are summed from every wire.jsonl under
.kimi_home/sessions/*/agents/{main,agent-*}/ (main, sub-agents, resume
sessions, compaction requests).

A usage.record is counted only when it is a complete receipt for an
llm.request:

  1. Incomplete usage (missing field or null, e.g. output=null) is dropped.
  2. An llm.request with no following usage.record — including when the next
     llm.request arrives first — is a failed query and is dropped.

Usage:
  python3 -m eval.common.build_audit_summary DUMP_ROOT [DUMP_ROOT ...]
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path

# Slot dir names are "<RUN_ID>_slot<N>" — same rule as audit_html_gen.py.
# Timestamp may be YYYYMMDD-HHMMSS, YYYYMMDD, or compact MMDDHHMMSS
# (e.g. c5l6-0912183504_slot0).
RUN_DIR_RE = re.compile(
    r"^(?:[A-Za-z0-9][A-Za-z0-9_.-]*[-_])?(?:\d{8}-\d{6}|\d{10}|\d{8})"
    r"(?:[-_][A-Za-z0-9_.-]+)?_slot\d+$"
)
# Launcher batches: results/<model>/<variant>/<RUN_ID>/ with run.json and task dirs.
BATCH_DIR_RE = re.compile(r"^\d{8}-\d{6}-[0-9a-f]{6}$")

USAGE_FIELDS = ("inputOther", "inputCacheRead", "inputCacheCreation", "output")
COST_FIELDS = ("Input-Cost", "inputCacheRead-Cost", "output-Cost", "total-Cost")

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from eval.common.paths import DEFAULT_PRICING

PRICING = json.loads(DEFAULT_PRICING.read_text(encoding="utf-8"))
MODEL_PRICES = PRICING["models"]
TIERED_PRICES = PRICING["tiered_models"]

CSV_FIELDS = [
    "Task",
    "Result",
    "Comment",
    "Critical Steps",
    "Subagent-Delegate",
    "Duration",
    "API Error Steps(main-agent/subagent)",
    "Checkpoints",
    "inputOther",
    "inputCacheRead",
    "inputCacheCreation",
    "output",
    "Input-Cost",
    "inputCacheRead-Cost",
    "output-Cost",
    "total-Cost",
    "audit.html",
]

EVAL_RE = re.compile(
    r"<b>Eval</b><span class=\"pill [a-z]+\">(PASS|FAIL|NO EVAL|[^<]*)</span>"
)
CK_RE = re.compile(r"<b>Checkpoints</b>([^<]*)")
DUR_RE = re.compile(r"<b>Duration</b>([^<]*)")
CRIT_RE = re.compile(
    r"<b>Critical Steps</b><span[^>]*>\s*(\d+)\s*</span>"
)
SUB_RE = re.compile(r"<b>Sub-agents</b>\s*(\d+)\s*")
CLAIM_RE = re.compile(r"<b>claim_done</b>(True|False|None|—|-)")
API_TOTAL_RE = re.compile(
    r"<b>API-error steps</b><span class=\"api-text\">(\d+)</span>"
)
SUB_API_TEXT_RE = re.compile(
    r"(\d+)\s+API-error sub-agent step\(s\) excluded"
)
KIMI_EXIT_RE = re.compile(
    r"exited rc=(\d+) claim_done=(\w+) -> status=(\w+)"
)
DONE_RE = re.compile(
    r"DONE\s+\S+\s+->\s+(\S+)\s+\(exit=(\d+),\s*(\d+)s"
)
API_ERROR_RE = re.compile(
    r"("
    r"provider_invalid|No providers available|MODEL_API_URL|RELAY_API_KEY|"
    r"APIStatusError|APITimeoutError|APIConnectionError|APIEmptyResponseError|"
    r"AuthenticationError|PermissionDeniedError|RateLimitError|"
    r"provider\.auth_error|"
    r"\b(?:429|401|403|502|503|504)\s+relay:|"
    r"relay:\s*\[Errno|proxy CONNECT failed|"
    r"['\"]type['\"]\s*:\s*['\"]relay_error['\"]|"
    r"invalid api key|api key invalid|quota exceeded|"
    r"empty response \(no content, no tool calls\)"
    r")",
    re.I,
)
# 403 鉴权/额度: team not allowed, quota, invalid key, provider.auth_error
AUTH_403_RE = re.compile(
    r"("
    r"provider\.auth_error|"
    r"403\s+team not allowed|"
    r"not allowed to access model|"
    r"Tried to access \S+|"
    r"quota exceeded|insufficient[_\s-]?quota|"
    r"invalid api key|api key invalid"
    r")",
    re.I,
)
FILTER_MARKERS = (
    "finishReason=filtered",
    "rawFinishReason=content_filter",
)
# kimi circuit-breaker after N identical tool calls in a row
SAME_TOOL_RE = re.compile(
    r"The same tool call has now been issued \d+ times in a row",
    re.I,
)
SAME_TOOL_STREAK = 6
# 并行 job 收尾中断: traj 转换模块在卸载过程中丢失
JOB_TEARDOWN_RE = re.compile(
    r"("
    r"No module named ['\"]kimi_harness\.traj_convert['\"]|"
    r"kimi_harness\.traj_convert|"
    r"in write_traj_logs"
    r")",
    re.I,
)
MAX_STEPS_RE = re.compile(
    r"loop\.max_steps_exceeded|Turn exceeded maxSteps|max_steps_exceeded",
    re.I,
)
CLAIM_TOOL_RE = re.compile(r"claim_done", re.I)
CLAIM_RESULT_HINT = "Task marked as done. The harness has been notified."


_TS_FULL_RE = re.compile(r"(20\d{6})-(\d{6})")
_TS_SHORT_RE = re.compile(r"-(\d{10})(?:_slot|$)")


def _slot_time_key(audit_html: Path) -> tuple[str, str]:
    """Sort key for latest slot: parsed timestamp, then directory name."""
    name = audit_html.parent.name
    full = _TS_FULL_RE.search(name)
    if full:
        return (full.group(1) + full.group(2), name)
    short = _TS_SHORT_RE.search(name)
    if short:
        return ("2026" + short.group(1), name)
    return ("", name)


def _slot_pages(task_dir: Path) -> list[Path]:
    """audit.html pages in task_dir/<run>_slotN/."""
    return [run_dir / "audit.html" for run_dir in task_dir.iterdir()
            if run_dir.is_dir() and RUN_DIR_RE.match(run_dir.name)
            and (run_dir / "audit.html").is_file()]


def _is_batch_dir(path: Path) -> bool:
    return bool(BATCH_DIR_RE.match(path.name)) or (path / "run.json").is_file()


def _is_smoke_batch(path: Path) -> bool:
    """Docker --smoke batches are offline infrastructure checks, not results."""
    try:
        return json.loads((path / "run.json").read_text()).get("smoke") is True
    except (OSError, ValueError, AttributeError):
        return False


def find_audit_htmls(dump_root: Path) -> list[tuple[str, Path]]:
    """Return (task_name, audit.html path) pairs.

    Supports these layouts:
      dump_root/task/audit.html
      dump_root/task/<run>_slotN/audit.html
      dump_root/<RUN_ID>/task/<RUN_ID>_slotN/audit.html   (launcher batches)
    Launcher batches are merged. If a task has several slot pages, keep the
    latest by parsed timestamp, so a re-run replaces earlier attempts.
    """
    if not dump_root.is_dir():
        return []
    found: dict[str, Path] = {}
    slots: dict[str, list[Path]] = {}
    for child in sorted(p for p in dump_root.iterdir() if p.is_dir()):
        if _is_batch_dir(child):
            if not _is_smoke_batch(child):
                for task_dir in sorted(p for p in child.iterdir() if p.is_dir()):
                    slots.setdefault(task_dir.name, []).extend(_slot_pages(task_dir))
        elif (child / "audit.html").is_file():
            found[child.name] = child / "audit.html"
        else:
            slots.setdefault(child.name, []).extend(_slot_pages(child))
    for task, pages in slots.items():
        if pages and task not in found:
            found[task] = sorted(pages, key=_slot_time_key)[-1]
    return [(name, path) for name, path in sorted(found.items())]


def expand_dump_roots(paths: list[Path], depth: int = 0, max_depth: int = 2) -> list[Path]:
    """Accept an experiment dir, a model dir, or the results root."""
    out: list[Path] = []
    for p in paths:
        if not p.is_dir():
            continue
        if find_audit_htmls(p):
            out.append(p)
        elif depth < max_depth:
            children = sorted(c for c in p.iterdir() if c.is_dir())
            out.extend(expand_dump_roots(children, depth + 1, max_depth))
    return out


def find_inner_dir(case_dir: Path) -> Path | None:
    try:
        children = list(case_dir.iterdir())
    except OSError:
        return None
    for model_dir in children:
        if model_dir.is_dir() and model_dir.name.startswith("kimi-code"):
            try:
                inners = list(model_dir.iterdir())
            except OSError:
                continue
            for inner in inners:
                if inner.is_dir() and inner.name.startswith("SingleUserTurn"):
                    return inner
    return None


def find_wire_paths(case_dir: Path) -> list[Path]:
    """All main / sub-agent wire.jsonl files across every session (incl. resume)."""
    inner = find_inner_dir(case_dir)
    if inner is None:
        return []
    sessions = inner / ".kimi_home" / "sessions"
    try:
        return sorted(sessions.glob("*/*/agents/*/wire.jsonl"))
    except OSError:
        return []


def infer_model_key(dump_root: Path) -> str | None:
    """Map results/<model>/<variant>[/<RUN_ID>] onto the pricing table."""
    known = set(MODEL_PRICES) | set(TIERED_PRICES)
    for name in (dump_root.name, dump_root.parent.name, dump_root.parent.parent.name):
        if name in known:
            return name
    return None


def rates_for(model_key: str | None, input_tokens: int) -> tuple[float, float, float]:
    """USD / 1M tokens for (miss, hit, output) on this request."""
    if model_key in TIERED_PRICES:
        tier = TIERED_PRICES[model_key]
        return tuple(tier["above"] if input_tokens > tier["input_token_threshold"] else tier["at_or_below"])
    if model_key in MODEL_PRICES:
        return tuple(MODEL_PRICES[model_key])
    return (0.0, 0.0, 0.0)


def cost_of_usage(parsed: dict[str, int], model_key: str | None) -> dict[str, float]:
    inp = (
        parsed["inputOther"]
        + parsed["inputCacheRead"]
        + parsed["inputCacheCreation"]
    )
    miss, hit, out = rates_for(model_key, inp)
    input_cost = parsed["inputOther"] / 1_000_000 * miss
    cache_cost = parsed["inputCacheRead"] / 1_000_000 * hit
    output_cost = parsed["output"] / 1_000_000 * out
    return {
        "Input-Cost": input_cost,
        "inputCacheRead-Cost": cache_cost,
        "output-Cost": output_cost,
        "total-Cost": input_cost + cache_cost + output_cost,
    }


def _int_or_none(value) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None


def complete_usage(usage) -> dict[str, int] | None:
    """Return the four token fields only when every field is present and numeric.

    A missing key or an explicit null (e.g. output=null) is incomplete and
    the whole receipt is discarded.
    """
    if not isinstance(usage, dict):
        return None
    out: dict[str, int] = {}
    for key in USAGE_FIELDS:
        if key not in usage:
            return None
        parsed = _int_or_none(usage[key])
        if parsed is None:
            return None
        out[key] = parsed
    return out


def sum_wire_usage(
    wire_path: Path, model_key: str | None = None
) -> tuple[dict[str, int], dict[str, float]]:
    """Pair llm.request with the next usage.record in file order.

    A new llm.request before a usage receipt, or a leftover request at EOF,
    is a failed query and is not counted. Incomplete usage.record values are
    also dropped. Compaction / resume requests use the same pairing.
    """
    totals = {k: 0 for k in USAGE_FIELDS}
    costs = {k: 0.0 for k in COST_FIELDS}
    pending = False
    try:
        fh = wire_path.open(errors="replace")
    except OSError:
        return totals, costs
    with fh:
        for line in fh:
            try:
                rec = json.loads(line)
            except Exception:
                continue
            typ = rec.get("type")
            if typ == "llm.request":
                pending = True
            elif typ == "usage.record":
                if not pending:
                    continue
                pending = False
                parsed = complete_usage(rec.get("usage"))
                if parsed is None:
                    continue
                for key in USAGE_FIELDS:
                    totals[key] += parsed[key]
                part = cost_of_usage(parsed, model_key)
                for key in COST_FIELDS:
                    costs[key] += part[key]
    return totals, costs


def case_token_usage(
    case_dir: Path, model_key: str | None = None
) -> tuple[dict[str, int], dict[str, float]]:
    totals = {k: 0 for k in USAGE_FIELDS}
    costs = {k: 0.0 for k in COST_FIELDS}
    for wire in find_wire_paths(case_dir):
        part, part_cost = sum_wire_usage(wire, model_key)
        for key in USAGE_FIELDS:
            totals[key] += part[key]
        for key in COST_FIELDS:
            costs[key] += part_cost[key]
    for key in ("Input-Cost", "inputCacheRead-Cost", "output-Cost"):
        costs[key] = round(costs[key], 6)
    costs["total-Cost"] = round(
        costs["Input-Cost"] + costs["inputCacheRead-Cost"] + costs["output-Cost"], 6
    )
    return totals, costs


def _section(html: str, section_id: str) -> str:
    start = html.find(f'<section id="{section_id}">')
    if start < 0:
        return ""
    end = html.find("<section id=", start + 10)
    if end < 0:
        end = html.find("</main>", start)
    return html[start:end] if end > 0 else html[start:]


def parse_audit_html(path: Path) -> dict:
    html = path.read_text(errors="replace")
    summary = _section(html, "summary")
    timeline = _section(html, "timeline")
    subrun = _section(html, "subrun")

    eval_m = EVAL_RE.search(summary)
    eval_txt = eval_m.group(1).strip() if eval_m else ""
    result = 1 if eval_txt == "PASS" else 0

    ck_m = CK_RE.search(summary)
    checkpoints = ck_m.group(1).strip() if ck_m else "—"
    if not checkpoints:
        checkpoints = "—"

    dur_m = DUR_RE.search(summary)
    duration = dur_m.group(1).strip() if dur_m else "—"

    crit_m = CRIT_RE.search(summary)
    critical = int(crit_m.group(1)) if crit_m else ""

    sub_m = SUB_RE.search(summary)
    n_subs = int(sub_m.group(1)) if sub_m else 0
    delegate = 1 if n_subs > 0 else 0

    main_api = timeline.count('class="step api-error"')
    sub_api = subrun.count('class="substep api-error"')
    total_m = API_TOTAL_RE.search(summary)
    sub_txt_m = SUB_API_TEXT_RE.search(subrun)
    if total_m and (main_api + sub_api) == 0:
        total = int(total_m.group(1))
        sub_api = int(sub_txt_m.group(1)) if sub_txt_m else 0
        main_api = max(0, total - sub_api)
    api_cell = f"{main_api}/{sub_api}"

    claim_m = CLAIM_RE.search(summary)
    claim_done = claim_m.group(1) if claim_m else None

    main_step_cls = re.findall(r'<div class="(step(?: api-error)?)"', timeline)
    last_main_api = bool(main_step_cls) and main_step_cls[-1] == "step api-error"
    last_sub_api = False
    for block in subrun.split('<details class="sub">')[1:]:
        sub_cls = re.findall(r'<div class="(substep(?: api-error)?)"', block)
        if sub_cls and sub_cls[-1] == "substep api-error":
            last_sub_api = True
            break

    return {
        "Result": result,
        "eval_txt": eval_txt,
        "Critical Steps": critical,
        "Subagent-Delegate": delegate,
        "Duration": duration,
        "API Error Steps(main-agent/subagent)": api_cell,
        "Checkpoints": checkpoints,
        "claim_done": claim_done,
        "main_api": main_api,
        "sub_api": sub_api,
        "last_main_api": last_main_api,
        "last_sub_api": last_sub_api,
    }


def _tool_names(event: dict) -> list[str]:
    names = []
    for tc in event.get("tool_calls") or []:
        if not isinstance(tc, dict):
            continue
        fn = tc.get("function") if isinstance(tc.get("function"), dict) else {}
        names.append(str(fn.get("name") or tc.get("name") or ""))
    return names


def _tool_sigs(event: dict) -> list[tuple[str, str]]:
    """(name, arguments) for each tool call on an assistant event."""
    sigs = []
    for tc in event.get("tool_calls") or []:
        if not isinstance(tc, dict):
            continue
        fn = tc.get("function") if isinstance(tc.get("function"), dict) else {}
        name = str(fn.get("name") or tc.get("name") or "")
        args = str(fn.get("arguments") or tc.get("arguments") or "")
        sigs.append((name, args))
    return sigs


def _same_tool_loop(events: list, text: str = "") -> bool:
    """True if the harness 6-in-a-row breaker fired near the end, or the
    last tool calls are the same (name, args) streak of SAME_TOOL_STREAK+."""
    if SAME_TOOL_RE.search(text or ""):
        tail = events[-20:] if len(events) > 20 else events
        for e in tail:
            if not isinstance(e, dict):
                continue
            blob = "\n".join(
                str(e.get(k) or "")
                for k in ("content", "_non_json", "error_message")
            )
            if SAME_TOOL_RE.search(blob):
                return True
        # reminder only in an earlier part of the traj: not the stop reason
    sigs: list[tuple[str, str]] = []
    for e in events:
        if isinstance(e, dict) and e.get("role") == "assistant":
            sigs.extend(_tool_sigs(e))
    if not sigs:
        return False
    last = sigs[-1]
    if not last[0]:
        return False
    n = 0
    for s in reversed(sigs):
        if s == last:
            n += 1
        else:
            break
    return n >= SAME_TOOL_STREAK


def _strip_trailing_meta(events: list) -> list:
    out = list(events)
    while out:
        e = out[-1]
        if not isinstance(e, dict):
            break
        if e.get("type") == "session.resume_hint":
            out.pop()
            continue
        nj = str(e.get("_non_json") or "")
        if nj.startswith("See log"):
            out.pop()
            continue
        break
    return out


def _is_api_error_event(event: dict) -> bool:
    if event.get("type") == "turn.step.retrying":
        msg = str(event.get("error_message") or "")
        if MAX_STEPS_RE.search(msg):
            return False
        return True
    blob = "\n".join(
        str(event.get(k) or "")
        for k in ("error_name", "error_message", "_non_json", "content")
    )
    if MAX_STEPS_RE.search(blob):
        return False
    if API_ERROR_RE.search(blob):
        return True
    name = str(event.get("error_name") or "")
    return "APIEmptyResponseError" in name or "APIError" in name


def _claim_index(events: list) -> int | None:
    for i, e in enumerate(events):
        if not isinstance(e, dict):
            continue
        if any(CLAIM_TOOL_RE.search(n) for n in _tool_names(e)):
            return i
        if e.get("role") == "tool" and CLAIM_RESULT_HINT in str(e.get("content") or ""):
            return i
    return None


def _last_assistant(events: list) -> dict | None:
    last = None
    for e in events:
        if isinstance(e, dict) and e.get("role") == "assistant":
            last = e
    return last


def _traj_text_has_filtered(text: str) -> bool:
    return any(m in text for m in FILTER_MARKERS)


def scan_trajs(inner: Path | None) -> dict:
    """Signals from main (and nested) traj.json files."""
    out = {
        "filtered": False,
        "auth_403": False,
        "same_tool_loop": False,
        "hit_100": False,
        "traj_api_steps": 0,
        "last_kind": "",
        "claimed_in_traj": False,
        "api_after_claim": False,
        "last_is_api": False,
    }
    if inner is None or not inner.is_dir():
        return out

    main_traj = inner / "traj.json"
    paths = [main_traj] if main_traj.is_file() else []

    main_data = None
    traj_text = ""
    for p in paths:
        try:
            text = p.read_text(errors="replace")
        except OSError:
            continue
        if p == main_traj:
            traj_text = text
        if _traj_text_has_filtered(text):
            out["filtered"] = True
        if AUTH_403_RE.search(text):
            out["auth_403"] = True
        if MAX_STEPS_RE.search(text):
            out["hit_100"] = True
        if p == main_traj:
            try:
                main_data = json.loads(text)
            except Exception:
                main_data = None

    if not isinstance(main_data, dict):
        if SAME_TOOL_RE.search(traj_text):
            out["same_tool_loop"] = True
        return out

    events = main_data.get("raw_events") or main_data.get("messages") or []
    if not isinstance(events, list):
        events = []
    out["same_tool_loop"] = _same_tool_loop(events, traj_text)

    api_idxs = []
    for i, e in enumerate(events):
        if isinstance(e, dict) and _is_api_error_event(e):
            api_idxs.append(i)
    out["traj_api_steps"] = len(api_idxs)
    claim_i = _claim_index(events)
    out["claimed_in_traj"] = claim_i is not None
    if claim_i is not None and any(i > claim_i for i in api_idxs):
        out["api_after_claim"] = True

    trimmed = _strip_trailing_meta(events)
    if trimmed and isinstance(trimmed[-1], dict):
        last = trimmed[-1]
        nj = str(last.get("_non_json") or "")
        if MAX_STEPS_RE.search(nj) or MAX_STEPS_RE.search(
            str(last.get("error_message") or "")
        ):
            out["last_kind"] = "max_steps"
            out["hit_100"] = True
        elif _is_api_error_event(last):
            out["last_kind"] = "api_error"
            out["last_is_api"] = True
        elif last.get("role") == "assistant":
            names = _tool_names(last)
            content = str(last.get("content") or "").strip()
            if any(CLAIM_TOOL_RE.search(n) for n in names):
                out["last_kind"] = "claim_done"
            elif names:
                out["last_kind"] = "tools"
            elif content:
                out["last_kind"] = "text"
            else:
                out["last_kind"] = "empty_assistant"
        elif last.get("role") == "tool":
            out["last_kind"] = "tool_result"
        else:
            out["last_kind"] = last.get("type") or last.get("role") or "other"

    if not out["last_kind"]:
        asst = _last_assistant(trimmed)
        if asst is not None:
            names = _tool_names(asst)
            content = str(asst.get("content") or "").strip()
            if any(CLAIM_TOOL_RE.search(n) for n in names):
                out["last_kind"] = "claim_done"
            elif names:
                out["last_kind"] = "tools"
            elif content:
                out["last_kind"] = "text"

    return out


def parse_stop_reason(case_dir: Path, rec: dict) -> str:
    """Comment label. Top-tier (timeout / 403_auth / same_tool_loop /
    job_teardown) first."""
    runlog = case_dir / "run.log"
    text = runlog.read_text(errors="replace") if runlog.exists() else ""
    inner = find_inner_dir(case_dir)
    traj = scan_trajs(inner)
    claimed_file = bool(inner and (inner / ".claim_done").is_file())
    claimed = (
        rec.get("claim_done") == "True"
        or claimed_file
        or traj["claimed_in_traj"]
        or bool(re.search(r"claim_done=True", text))
    )

    timeout = bool(re.search(r"overall timeout\s+\d+s", text, re.I))
    auth_403 = traj["auth_403"] or bool(AUTH_403_RE.search(text))
    same_tool = bool(traj["same_tool_loop"])
    job_teardown = bool(JOB_TEARDOWN_RE.search(text))
    preprocess = bool(re.search(r"\[kimi\] aborting: preprocess failed", text))

    # Top-tier stop reasons (same priority group). Overlap order:
    # timeout > 403_auth > same_tool_loop > job_teardown.
    if timeout:
        return "timeout"
    if auth_403:
        return "403_auth"
    if same_tool and not claimed:
        return "same_tool_loop"
    if job_teardown:
        return "job_teardown"

    if preprocess:
        return "preprocess_failed"

    n_api = int(rec.get("main_api") or 0) + int(rec.get("sub_api") or 0)
    mixed_api = n_api > 0 or traj["traj_api_steps"] > 0
    last_api = (
        traj["last_is_api"]
        or bool(rec.get("last_main_api"))
        or (not claimed and bool(rec.get("last_sub_api")))
    )

    if traj["filtered"]:
        return "filtered"

    # Last step of main (or of a sub, if the run never claimed) is API-error.
    if last_api and claimed:
        return "case_summary_missing"

    if traj["hit_100"]:
        if mixed_api:
            return "api_error_cause_100_step_limit"
        return "100_step_limit"

    if last_api and not claimed:
        return "API Error"

    if not claimed and traj["last_kind"] == "text":
        return "terminate_with_text"

    km = KIMI_EXIT_RE.search(text)
    if km:
        done = km.group(2) == "True"
        status = km.group(3)
        if done:
            return "claim_done"
        if status == "failed":
            return "no_claim_done"
        return status

    if rec.get("claim_done") == "True" or claimed:
        return "claim_done"
    if rec.get("claim_done") == "False":
        return "no_claim_done"

    dm = DONE_RE.search(text)
    if dm:
        return dm.group(1)
    return "unknown"


def collect_rows(dump_root: Path) -> list[dict]:
    rows = []
    model_key = infer_model_key(dump_root)
    if model_key is None:
        print(f"[warn] no pricing key for {dump_root}", file=sys.stderr)
    for task, audit in find_audit_htmls(dump_root):
        rec = parse_audit_html(audit)
        rec["Task"] = task
        case_dir = audit.parent
        rec["Comment"] = parse_stop_reason(case_dir, rec)
        tokens, costs = case_token_usage(case_dir, model_key)
        rec.update(tokens)
        rec.update(costs)
        rec["audit.html"] = str(audit.resolve())
        rows.append({k: rec[k] for k in CSV_FIELDS})
    return rows


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        w.writeheader()
        w.writerows(rows)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "dump_root",
        nargs="+",
        type=Path,
        help="Experiment directory or parent directory containing experiments",
    )
    ap.add_argument(
        "-o", "--output",
        type=Path,
        default=None,
        help="Output CSV path (only valid with a single experiment dir)",
    )
    args = ap.parse_args(argv[1:])
    roots = expand_dump_roots([p.resolve() for p in args.dump_root])
    if not roots:
        print("[error] no experiment directories with audit.html found",
              file=sys.stderr)
        return 1
    if args.output is not None and len(roots) != 1:
        print("[error] --output requires exactly one experiment directory",
              file=sys.stderr)
        return 1

    rc = 0
    for dump_root in roots:
        out = args.output.resolve() if args.output else dump_root / "summary.csv"
        if not dump_root.is_dir():
            print(f"[error] not a directory: {dump_root}", file=sys.stderr)
            rc = 1
            continue
        rows = collect_rows(dump_root)
        for row in rows:
            row["audit.html"] = Path(os.path.relpath(row["audit.html"], out.parent)).as_posix()
        write_csv(out, rows)
        n = len(rows)
        n_pass = sum(1 for r in rows if r["Result"] == 1)
        n_sub = sum(1 for r in rows if r["Subagent-Delegate"] == 1)
        tok = {k: sum(int(r[k]) for r in rows) for k in USAGE_FIELDS}
        usd = {k: sum(float(r[k]) for r in rows) for k in COST_FIELDS}
        comments: dict[str, int] = {}
        for r in rows:
            comments[r["Comment"]] = comments.get(r["Comment"], 0) + 1
        print(f"[ok] {out}")
        print(f"     tasks={n}  pass={n_pass}  fail_or_noeval={n - n_pass}  "
              f"with_subagent={n_sub}  model={infer_model_key(dump_root)}")
        print(f"     comment  " + "  ".join(
            f"{k}={v}" for k, v in sorted(comments.items(), key=lambda x: (-x[1], x[0]))
        ))
        print(f"     tokens  inputOther={tok['inputOther']}  "
              f"inputCacheRead={tok['inputCacheRead']}  "
              f"inputCacheCreation={tok['inputCacheCreation']}  "
              f"output={tok['output']}")
        print(f"     usd     Input-Cost={usd['Input-Cost']:.4f}  "
              f"inputCacheRead-Cost={usd['inputCacheRead-Cost']:.4f}  "
              f"output-Cost={usd['output-Cost']:.4f}  "
              f"total-Cost={usd['total-Cost']:.4f}")
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
