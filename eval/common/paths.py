"""Dataset and evaluation material locations, independent of the working directory."""
from pathlib import Path
import os

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
EVAL_DIR = REPO_ROOT / "eval"
TASK_CATEGORIES_DIR = DATA_DIR / "task_categories"
DA_EVAL_DIR = EVAL_DIR / "delegation_appropriateness"
DEFAULT_ORACLE = DATA_DIR / "oracle166"
DEFAULT_GT = DA_EVAL_DIR / "delegate_gt_tag"
DEFAULT_CACHE = DA_EVAL_DIR / "delegate_llm_tag_cache"
DEFAULT_PRICING = EVAL_DIR / "orchestration_utilities" / "pricing.json"


def repository_path(value: str | Path) -> Path:
    """Resolve stored repository-relative metadata; accept legacy absolute paths."""
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def portable_path(value: str | Path) -> str:
    """Serialize a path relative to the checkout, including external export inputs."""
    return Path(os.path.relpath(Path(value).resolve(), REPO_ROOT)).as_posix()
