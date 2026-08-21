from __future__ import annotations

import json
import os
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import yaml

from .paths import ensure_if_root, if_root
from .schema import SchemaError, validate_obj
from .state import TransitionError, assert_transition


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@contextmanager
def file_lock(path: Path, timeout_s: float = 10.0):
    path.parent.mkdir(parents=True, exist_ok=True)
    start = time.time()
    while True:
        try:
            fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            break
        except FileExistsError:
            if time.time() - start > timeout_s:
                raise TimeoutError(f"lock timeout: {path}")
            time.sleep(0.05)
    try:
        yield
    finally:
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def atomic_write_yaml(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    os.replace(tmp, path)


def load_yaml(path: Path, default=None):
    if not path.is_file():
        return default
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def append_jsonl(path: Path, rec: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def load_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


class Store:
    def __init__(self, root: str | Path | None = None):
        self.root = ensure_if_root(if_root(root))

    @property
    def questions_dir(self) -> Path:
        return self.root / "graph" / "questions"

    @property
    def idseq(self) -> Path:
        return self.root / "graph" / ".idseq"

    @property
    def idlock(self) -> Path:
        return self.root / "graph" / ".idlock"

    @property
    def edges(self) -> Path:
        return self.root / "graph" / "edges.jsonl"

    @property
    def decisions(self) -> Path:
        return self.root / "memory" / "decisions.jsonl"

    @property
    def dissent_log(self) -> Path:
        return self.root / "dissent" / "dissent_log.jsonl"

    def alloc_question_id(self, run_id: str, actor: str = "cycle") -> str:
        if actor != "cycle":
            raise PermissionError("alloc_question_id is IfCycle-only (V9)")
        parts = run_id.split("-")
        date = parts[1][:8] if len(parts) > 1 else datetime.now(timezone.utc).strftime("%Y%m%d")
        with file_lock(self.idlock, 10):
            seq = load_yaml(self.idseq) or {"date": date, "n": 0}
            if seq.get("date") != date:
                seq = {"date": date, "n": 0}
            seq["n"] = int(seq["n"]) + 1
            atomic_write_yaml(self.idseq, seq)
        return f"Q-{date}-{seq['n']:04d}"

    def reuse_or_mint(self, run_dir: Path, local_id: str, run_id: str) -> str:
        mp_path = run_dir / "local_id_map.yaml"
        mp = load_yaml(mp_path) or {}
        if local_id in mp:
            return mp[local_id]
        qid = self.alloc_question_id(run_id, actor="cycle")
        mp[local_id] = qid
        atomic_write_yaml(mp_path, mp)
        return qid

    def q_path(self, qid: str) -> Path:
        return self.questions_dir / f"{qid}.yaml"

    def load_question(self, qid: str) -> dict | None:
        p = self.q_path(qid)
        return load_yaml(p) if p.is_file() else None

    def iter_questions(self) -> list[dict]:
        out = []
        for p in sorted(self.questions_dir.glob("Q-*.yaml")):
            data = load_yaml(p)
            if data:
                out.append(data)
        return out

    def load_status(self, *st: str) -> list[dict]:
        wanted = set(st)
        return [q for q in self.iter_questions() if q.get("status") in wanted]

    def write_question(self, q: dict, actor: str, reviewer_ok: bool = False) -> str:
        validate_obj("qo", q)
        prev = self.load_question(q["question_id"])
        if prev:
            assert_transition(prev["status"], q["status"], actor, reviewer_ok)
            q["version"] = int(prev.get("version", 1)) + 1
            q["last_verified_at"] = now_iso()
            rev = self.root / "graph" / "revisions" / f"{q['question_id']}-v{prev.get('version', 1)}.yaml"
            atomic_write_yaml(rev, prev)
        else:
            if q["status"] != "DRAFT":
                raise ValueError("first write must be DRAFT")
            q["version"] = 1
            q.setdefault("created_at", now_iso())
            q.setdefault("last_verified_at", now_iso())
        self._require_lineage(q)
        atomic_write_yaml(self.q_path(q["question_id"]), q)
        self.append_edges(q)
        return q["question_id"]

    def _require_lineage(self, q: dict) -> None:
        lin = q.get("lineage") or {}
        for k in ("generated_by", "run_id", "operator", "evidence_kind"):
            if k == "operator":
                if not q.get("operator"):
                    raise SchemaError("lineage/operator blank")
            elif not lin.get(k):
                raise SchemaError(f"lineage.{k} blank")

    def _edge_keys(self) -> set[tuple]:
        keys = set()
        for rec in load_jsonl(self.edges):
            keys.add((rec.get("src"), rec.get("rel"), rec.get("dst")))
        return keys

    def append_edges(self, q: dict) -> None:
        seen = self._edge_keys()
        ts = now_iso()

        def add(rel: str, dst: str) -> None:
            if not dst:
                return
            key = (q["question_id"], rel, dst)
            if key in seen:
                return
            append_jsonl(self.edges, {"ts": ts, "src": q["question_id"], "rel": rel, "dst": dst})
            seen.add(key)

        for p in (q.get("lineage") or {}).get("parents") or []:
            add("parent", p)
        for d in q.get("derived_from") or []:
            add("derived_from", d)
        for c in q.get("contradictions") or []:
            add("contradicts", c)

    def record_decision(self, rec: dict) -> None:
        rec = dict(rec)
        rec.setdefault("ts", now_iso())
        validate_obj("decision_rec", rec)
        append_jsonl(self.decisions, rec)

    def query_avoid_patterns(self, domain: str, n: int = 8) -> list[str]:
        """What the next run is told to avoid: defects in questions, only.

        A verdict can be about the question or about us. "The falsifier needs
        data nobody can obtain" is the first; "that grid costs tens of millions
        and we are not a frontier lab" is the second, and teaching a generator
        the second is how a question about the world became a question about
        our budget between RUN-20260820-live6 and RUN-20260821-live8.

        Rows written before this axis existed carry no `reason_kind`. They are
        read as question defects, which is exactly how they behaved, rather
        than reclassified after the fact by guessing at someone's wording.
        """
        rows = [
            r for r in load_jsonl(self.decisions)
            if r.get("decision") == "reject" and r.get("domain") == domain and r.get("reason")
            and not r.get("informational")
            and (r.get("reason_kind") or "question_defect") == "question_defect"
        ]
        return [r["reason"] for r in rows[-n:]]

    def append_dissent(self, rec: dict) -> None:
        append_jsonl(self.dissent_log, rec)

    def load_dissent(self, run_id: str | None = None) -> list[dict]:
        rows = load_jsonl(self.dissent_log)
        if run_id:
            rows = [r for r in rows if r.get("run_id") == run_id]
        return rows


class Drop(Exception):
    pass


class Blocked(Exception):
    pass
