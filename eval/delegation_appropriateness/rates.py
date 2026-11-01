"""Task-level under- and over-delegation rates (paper Eq. 1)."""
import json
from pathlib import Path


def load_gt_need(index_path: Path) -> dict[str, bool]:
    data = json.loads(index_path.read_text(encoding="utf-8"))
    return {item["task"]: bool(item["need_delegation"]) for item in data["tasks"]}


def load_delegated_from_task_metrics(directory: Path) -> dict[str, bool]:
    """Read observed non-planning delegation; missing traces remain unknown."""
    rows = json.loads((directory / "task_metrics.json").read_text(encoding="utf-8"))
    return {
        row["task"]: row["delegated"] for row in rows
        if row.get("coverage") and isinstance(row.get("delegated"), bool)
    }


def delegation_rates(gt_need: dict[str, bool], delegated: dict[str, bool]) -> dict:
    """Compute rates over annotated tasks with an observed delegation decision."""
    need = [task for task, value in gt_need.items() if value and task in delegated]
    no_need = [task for task, value in gt_need.items() if not value and task in delegated]
    under = sum(not delegated[task] for task in need)
    over = sum(delegated[task] for task in no_need)
    return {
        "udr": under / len(need) if need else None,
        "odr": over / len(no_need) if no_need else None,
        "udr_cnt": under,
        "odr_cnt": over,
        "n_need": len(need),
        "n_noneed": len(no_need),
        "n_missing": sum(task not in delegated for task in gt_need),
    }
