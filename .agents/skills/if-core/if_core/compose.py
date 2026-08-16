from __future__ import annotations

from pathlib import Path

from .const import MECH
from .gates import mechanical_gates
from .store import Blocked, Store, now_iso


def empty_dissent(s: dict) -> dict:
    return {
        "local_id": s["local_id"],
        "examiner": None,
        "attacks": [],
        "kill_count": 0,
        "verdict": "SURVIVED",
    }


def stamp_lineage(seed: dict, src_lwar: str, run_id: str) -> dict:
    claimed = (seed.get("lineage") or {}).get("generated_by")
    if claimed not in {None, src_lwar}:
        from .store import Drop
        raise Drop("forged generated_by")
    seed.setdefault("lineage", {})
    seed["lineage"]["generated_by"] = src_lwar
    seed["lineage"]["run_id"] = run_id
    return seed


def materialize_qo(seed: dict, dissent: dict, qid: str, hints: list[str], ts: str) -> dict:
    q = dict(seed)
    q.update({
        "question_id": qid,
        "status": "DRAFT",
        "contradictions": seed.get("contradictions") or [],
        "estimated_cost": seed.get("estimated_cost") or "",
        "created_at": ts,
        "last_verified_at": ts,
        "dissent": [a for a in dissent.get("attacks", []) if a.get("result") != "miss"],
        "gate_results": mechanical_gates(seed, hints),
        "human_review": {"status": "pending", "reviewer": "", "note": ""},
        "scores": {},
        "version": 1,
    })
    return q


def compose(store: Store, run_dir: Path, run_id: str, seeds: list, dissents: dict,
            cards: dict, hints_by_kind: dict, mode: str) -> list[dict]:
    out = []
    ts = now_iso()
    for s in seeds:
        d = dissents.get(s["local_id"])
        if d is None:
            if mode == "normal":
                raise Blocked("protocol_incomplete")
            d = empty_dissent(s)
        c = cards.get(s["local_id"]) or {
            "verdict": "GATE_FAIL", "scores": {}, "failed_gate": "missing_card",
        }
        qid = store.reuse_or_mint(run_dir, s["local_id"], run_id)
        hints = hints_by_kind.get(s["lineage"]["evidence_kind"], [])
        q = materialize_qo(s, d, qid, hints, ts)
        mech_fail = any(q["gate_results"].get(g) == "fail" for g in MECH)
        if d.get("verdict") == "KILLED" or c.get("verdict") == "GATE_FAIL" or mech_fail:
            nxt = "REJECTED"
        elif q.get("question_class") in {"normative", "meta"}:
            nxt = "DORMANT"
        else:
            q["scores"] = c.get("scores") or {}
            nxt = "SCORED"
        store.write_question(q, actor="oa")
        q["status"] = nxt
        store.write_question(q, actor="oa")
        d = dict(d)
        d["question_id"] = qid
        d["run_id"] = run_id
        store.append_dissent(d)
        out.append(q)
    return out
