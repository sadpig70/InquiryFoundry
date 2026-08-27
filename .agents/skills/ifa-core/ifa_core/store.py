"""The .ifa store, and the one-way window into .if.

Decision A1: this package writes only under .ifa. The question store is an
input, never a surface — an AnswerObject holds a question_id and the question
object never learns it was predicted about. `read_adopted` opens files
read-only and nothing in this package constructs a write path under .if;
`assert_outside_if` is the guard that keeps that true when paths are built
from data.

Naming discipline lives in the schema, not the folder name: `kind` has one
legal value, "predicted". The day a real experiment answers one of these
questions, adding "answered" to the enum is a deliberate schema change with
its own review — not a drift.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SKILLS = Path(__file__).resolve().parents[2]
if str(_SKILLS / "if-core") not in sys.path:
    sys.path.insert(0, str(_SKILLS / "if-core"))

# Role-agnostic utilities only (decision A2); if_core files stay unmodified.
from if_core.store import atomic_write_yaml, load_yaml, now_iso  # noqa: E402

ANSWER_STATES = ("DRAFT", "SCORED", "REGISTERED", "DISCARDED")


class IfaStore:
    def __init__(self, ifa_root: str = ".ifa", if_root: str = ".if"):
        self.root = Path(ifa_root)
        self.if_root = Path(if_root)

    # ---------- read-only window into .if ----------

    def read_adopted(self) -> list[dict]:
        """Adopted questions, straight off the question store, unmodified."""
        out = []
        base = self.if_root / "graph" / "questions"
        if not base.is_dir():
            return out
        for p in sorted(base.rglob("*.yaml")):
            q = load_yaml(p)
            if isinstance(q, dict) and q.get("status") == "ADOPTED":
                out.append(q)
        return out

    def assert_outside_if(self, path: Path) -> Path:
        """Invariant 1: no write path may point into the question store."""
        resolved = Path(path).resolve()
        if_resolved = self.if_root.resolve()
        if if_resolved == resolved or if_resolved in resolved.parents:
            raise PermissionError(f"refusing to write inside .if: {path}")
        return Path(path)

    # ---------- .ifa surfaces ----------

    def run_dir(self, run_id: str) -> Path:
        d = self.root / "runs" / run_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def answers_dir(self) -> Path:
        d = self.root / "graph" / "answers"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def reports_dir(self) -> Path:
        d = self.root / "reports"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def write_answer(self, ans: dict) -> Path:
        if ans.get("kind") != "predicted":
            raise ValueError("kind must be 'predicted' (decision A3)")
        if ans.get("status") not in ANSWER_STATES:
            raise ValueError(f"unknown status: {ans.get('status')}")
        path = self.answers_dir() / f"{ans['answer_id']}.yaml"
        self.assert_outside_if(path)
        ans = dict(ans)
        ans["updated_at"] = now_iso()
        atomic_write_yaml(path, ans)
        return path

    def load_answer(self, answer_id: str) -> dict | None:
        p = self.answers_dir() / f"{answer_id}.yaml"
        return load_yaml(p) if p.is_file() else None

    def load_answers(self, run_id: str | None = None) -> list[dict]:
        out = []
        for p in sorted(self.answers_dir().glob("ANS-*.yaml")):
            a = load_yaml(p)
            if isinstance(a, dict) and (run_id is None or a.get("run_id") == run_id):
                out.append(a)
        return out
