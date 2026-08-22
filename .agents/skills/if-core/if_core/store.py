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

    # Fable 5's decision, 2026-08-22. Untested initial values by its own
    # account, to be moved by the verification it specified — not by taste.
    REGISTRY_ENTER_RUNS = 2      # seen in this many distinct runs to be entered
    REGISTRY_DISUSE_RUNS = 4     # no new instance within this many closed runs
    REGISTRY_CAP = 12            # per domain
    RECENT_RUNS = 3              # verbatim window spans this many closed runs
    RECENT_PER_RUN = 3           # at most this many reasons from any one run

    def _defect_rows(self, domain: str) -> list[dict]:
        return [
            r for r in load_jsonl(self.decisions)
            if r.get("decision") == "reject" and r.get("domain") == domain
            and r.get("reason") and not r.get("informational")
            and (r.get("reason_kind") or "question_defect") == "question_defect"
        ]

    @staticmethod
    def _run_order(rows: list[dict]) -> list[str]:
        """Closed runs oldest-first. The log is append-only, so its order is
        the order runs closed."""
        order = []
        for r in rows:
            rid = r.get("run_id")
            if rid and rid not in order:
                order.append(rid)
        return order

    def avoid_codes(self) -> dict:
        """The taxonomy, and whether it is in force.

        A machine reviewer proposed these codes from its own verdict history.
        It does not enact them: the taxonomy is the coordinate system every
        later rejection is expressed in, and a reviewer enacting its own would
        institutionalise its bias. Until a person ratifies, nothing keys on it.
        """
        doc = load_yaml(self.root / "memory" / "avoid_codes.yaml")
        if not isinstance(doc, dict):
            return {"ratified": False, "codes": []}
        return {"ratified": bool(doc.get("ratified")),
                "codes": list(doc.get("codes") or []),
                "legacy": list((doc.get("legacy_patterns") or {}).get("map") or [])}

    @staticmethod
    def pattern_code(pattern: str) -> str | None:
        """`CODE — qualifier` -> CODE. The key is the code alone.

        Free text failed as a key because the same reviewer wrote the same
        defect two different ways across live11 and live12, so the registry
        never entered anything. The fix is not stricter discipline but a closed
        list to choose from — the qualifier stays free so the specificity that
        drives repairs survives.
        """
        head = str(pattern or "").split("—", 1)[0].strip()
        head = head.split(" - ", 1)[0].strip()
        return head or None

    def registry_key(self, pattern: str) -> str:
        """Code when the taxonomy is in force, otherwise the whole line.

        Patterns written before the taxonomy are free text and carry no code.
        They are mapped here, when the derived view is computed, rather than
        rewritten: `decisions.jsonl` is append-only and what a reviewer wrote
        stays what it wrote.
        """
        text = str(pattern or "").strip()
        codes = self.avoid_codes()
        if not codes["ratified"]:
            return text
        for entry in codes.get("legacy", []):
            if entry.get("prefix") and text.startswith(entry["prefix"]):
                return entry["code"]
        return self.pattern_code(text) or text

    def avoid_registry(self, domain: str) -> list[dict]:
        """Patterns that recurred, kept until they fall out of use.

        Recomputed from `decisions.jsonl` every time rather than maintained
        incrementally. Fable flagged a second source of truth as the risk in
        its own design; deriving it means there is only ever one.

        A mass rejection cannot flush this: entry is by recurrence across runs,
        and exit is by a pattern going unseen for `REGISTRY_DISUSE_RUNS` closed
        runs — not by being pushed out of a fixed-size queue.
        """
        rows = [r for r in self._defect_rows(domain) if (r.get("pattern") or "").strip()]
        order = self._run_order(rows)
        recent_runs = set(order[-self.REGISTRY_DISUSE_RUNS:])
        seen: dict[str, dict] = {}
        for r in rows:
            key = self.registry_key(r["pattern"])
            entry = seen.setdefault(key, {"pattern": key, "runs": []})
            if r.get("run_id") and r["run_id"] not in entry["runs"]:
                entry["runs"].append(r["run_id"])
        entries = [
            e for e in seen.values()
            if len(e["runs"]) >= self.REGISTRY_ENTER_RUNS
            and e["runs"][-1] in recent_runs
        ]
        # Oldest last-sighting drops first when over the cap.
        entries.sort(key=lambda e: order.index(e["runs"][-1]))
        return entries[-self.REGISTRY_CAP:]

    def dormant_codes(self) -> set[str]:
        """Codes that were used and then fell out of use.

        Retirement is disuse, not eviction — a code stops being carried when
        nothing has matched it for `REGISTRY_DISUSE_RUNS` closed runs. Computed
        across domains, because the codes name structural defects in a test
        design and nothing about them is domain-specific: every one of the eight
        seeds describes a broken argument, not a fact about scaling laws.
        A code that has never been used is not dormant — it has not had its turn.
        """
        rows = [r for r in load_jsonl(self.decisions)
                if r.get("decision") == "reject" and r.get("reason")
                and not r.get("informational") and (r.get("pattern") or "").strip()
                and (r.get("reason_kind") or "question_defect") == "question_defect"]
        order = self._run_order(rows)
        recent = set(order[-self.REGISTRY_DISUSE_RUNS:])
        last_seen: dict[str, str] = {}
        for r in rows:
            last_seen[self.registry_key(r["pattern"])] = r.get("run_id")
        return {code for code, run in last_seen.items() if run not in recent}

    def write_avoid_registry(self, domain: str) -> Path:
        """Publish the derived view. Nothing reads this file — it exists so a
        person can see what the loop is carrying."""
        path = self.root / "memory" / "avoid_registry.yaml"
        doc = load_yaml(path) if path.is_file() else None
        doc = doc if isinstance(doc, dict) else {
            "schema_version": "if.avoid-registry.v1", "domains": {}}
        doc.setdefault("domains", {})[domain] = {
            "patterns": self.avoid_registry(domain),
            "rebuilt_at": now_iso(),
        }
        atomic_write_yaml(path, doc)
        return path

    def query_avoid_patterns(self, domain: str) -> dict:
        """Two blocks, because one shape cannot carry both jobs.

        `patterns` persists: entry by recurrence, exit by disuse, so a mass
        rejection does not flush what several runs agreed was a trap.
        `recent_reasons` is verbatim, because that specificity is what made a
        rejected question come back repaired — RUN-20260822-live10g answered a
        named contradiction in its criterion with equal-size subgrids and an
        equivalence margin, a different question rather than the same one again.

        Stratified by run, at most `RECENT_PER_RUN` from any one, so a single
        thirteen-reject close takes a third of the window and not all of it.
        Within a run, reasons whose pattern the registry already carries go
        last: the registry covers them, so their prose is the redundant part.
        """
        rows = self._defect_rows(domain)
        order = self._run_order(rows)
        registered = {e["pattern"] for e in self.avoid_registry(domain)}
        keyed = self.registry_key
        recent, by_run = [], {}
        for r in rows:
            by_run.setdefault(r.get("run_id"), []).append(r)
        for run_id in order[-self.RECENT_RUNS:]:
            picks = by_run.get(run_id) or []
            fresh = [r for r in picks if keyed(r.get("pattern") or "") not in registered]
            covered = [r for r in picks if keyed(r.get("pattern") or "") in registered]
            recent.extend((fresh + covered)[: self.RECENT_PER_RUN])
        codes = self.avoid_codes()
        if codes["ratified"]:
            # Definitions carry across domains; only the verbatim reasons are
            # domain-scoped. A new domain therefore opens with the taxonomy
            # already in hand rather than with an empty window — the cold start
            # that cost `scaling` its first several runs.
            dormant = self.dormant_codes()
            patterns = ["%s — %s" % (c["code"], " ".join(str(c.get("def") or "").split()))
                        for c in codes["codes"] if c["code"] not in dormant]
        else:
            patterns = [e["pattern"] for e in self.avoid_registry(domain)]
        return {"patterns": patterns, "recent_reasons": [r["reason"] for r in recent]}

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
