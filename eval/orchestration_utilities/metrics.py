"""Orchestration utilities over paired MAD-SAE and SA observations (Eq. 3)."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TaskRow:
    task: str
    result: int          # 1=success 0=fail
    critical_steps: int
    delegated: bool      # Subagent-Delegate column
    cost: float          # total-Cost (USD)


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


def load_summary_csv(path: Path) -> dict[str, TaskRow]:
    if not path.is_file():
        return {}
    out: dict[str, TaskRow] = {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            task = (row.get("Task") or "").strip()
            if not task:
                continue
            out[task] = TaskRow(
                task=task,
                result=_to_int(row.get("Result")),
                critical_steps=_to_int(row.get("Critical Steps")),
                delegated=_to_int(row.get("Subagent-Delegate")) == 1,
                cost=_to_float(row.get("total-Cost")),
            )
    return out


def utilities(
    mad_rows: dict[str, TaskRow],
    sa_rows: dict[str, TaskRow],
    include_failed: bool = False,
    delegated_map: dict[str, bool] | None = None,
) -> dict | None:
    """Compute utilities on paired tasks with observed non-planning delegation.

    Unknown delegation decisions are excluded. Episode steps and costs still
    include planning overhead. With no decisions, no utility can be computed.
    """
    delegated_map = delegated_map or {}
    d_sub = [t for t in mad_rows if delegated_map.get(t, False) and t in sa_rows]
    if not d_sub:
        return None

    # U_p: success-rate over D_sub
    mad_succ_cnt = sum(mad_rows[t].result for t in d_sub)
    sa_succ_cnt = sum(sa_rows[t].result for t in d_sub)
    sr_mad = mad_succ_cnt / len(d_sub)
    sr_sa = sa_succ_cnt / len(d_sub)
    u_p = sr_mad / (sr_mad + sr_sa) if (sr_mad + sr_sa) > 0 else None

    # Resource means use MAD-successful tasks on both sides, regardless of SA
    # success. include_failed selects the larger diagnostic population.
    mad_ok = [t for t in d_sub if mad_rows[t].result == 1]
    pool = d_sub if include_failed else mad_ok
    u_e = u_c = None
    cs_mad = cs_sa = c_mad = c_sa = None
    if pool:
        cs_mad = sum(mad_rows[t].critical_steps for t in pool) / len(pool)
        cs_sa = sum(sa_rows[t].critical_steps for t in pool) / len(pool)
        if (cs_mad + cs_sa) > 0:
            u_e = cs_sa / (cs_mad + cs_sa)
        c_mad = sum(mad_rows[t].cost for t in pool) / len(pool)
        c_sa = sum(sa_rows[t].cost for t in pool) / len(pool)
        if (c_mad + c_sa) > 0:
            u_c = c_sa / (c_mad + c_sa)

    return {
        "n_dsub": len(d_sub),
        "n_mad_ok": len(mad_ok),
        "n_pool": len(pool),
        "mad_succ_cnt": mad_succ_cnt,
        "sa_succ_cnt": sa_succ_cnt,
        "sr_mad": sr_mad,
        "sr_sa": sr_sa,
        "cs_mad": cs_mad,
        "cs_sa": cs_sa,
        "c_mad": c_mad,
        "c_sa": c_sa,
        "U_p": u_p,
        "U_e": u_e,
        "U_c": u_c,
    }
