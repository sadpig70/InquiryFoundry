from __future__ import annotations

import os
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parent.parent


def if_root(explicit: str | Path | None = None) -> Path:
    raw = explicit or os.environ.get("IF_ROOT") or (Path.cwd() / ".if")
    return Path(raw).resolve()


def ensure_if_root(root: Path) -> Path:
    for sub in (
        "graph/questions",
        "graph/revisions",
        "memory",
        "dissent",
        "runs",
        "corpus",
    ):
        (root / sub).mkdir(parents=True, exist_ok=True)
    return root
