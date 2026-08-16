from __future__ import annotations

from pathlib import Path

import yaml

from .const import PARETO_AXES
from .store import Blocked, Store, atomic_write_yaml, load_yaml, now_iso


def nondominated(cands: list[dict], axes: list[str], k: int = 12) -> list[dict]:
    def score(q, ax):
        v = (q.get("scores") or {}).get(ax)
        return float(v) if v is not None else 0.0

    def dominates(a, b):
        ge = all(score(a, ax) >= score(b, ax) for ax in axes)
        gt = any(score(a, ax) > score(b, ax) for ax in axes)
        return ge and gt

    front = []
    for c in cands:
        if any(dominates(o, c) for o in cands if o is not c):
            continue
        front.append(c)
    if len(front) < k:
        rest = [c for c in cands if c not in front]
        rest.sort(key=lambda q: q["question_id"])
        front.extend(rest)
    front.sort(key=lambda q: q["question_id"])
    return front[:k]


def open_review(store: Store, run_dir: Path, run_id: str, qos: list[dict]) -> dict:
    scored = [q for q in qos if q["status"] == "SCORED"]
    portfolio = nondominated(scored, PARETO_AXES, 12)
    pids = {q["question_id"] for q in portfolio}
    dissent_p = [
        q for q in qos
        if q["status"] in {"REJECTED", "SCORED", "DORMANT"}
        and any(a.get("result") in {"wound", "kill"} for a in q.get("dissent") or [])
    ]
    mech_rej = [q for q in qos if q["status"] == "REJECTED"]
    seen, cards = set(), []
    for q in portfolio + dissent_p + mech_rej:
        qid = q["question_id"]
        if qid in seen:
            continue
        seen.add(qid)
        info = q["status"] == "REJECTED" and qid not in pids
        cards.append({
            "question_id": qid,
            "question": q["question"],
            "minimal_test": q.get("minimal_test") or {},
            "decision": "reject" if info else "pending",
            "reason": "mechanical_rejected" if info else "",
            "informational": info,
            "checks": {"already_answered": None, "test_runnable": None, "duplicate": None},
            "bucket": "informational" if info else (
                "dissent" if q in dissent_p and qid not in pids else "pareto"
            ),
        })
    doc = {
        "run_id": run_id,
        "reviewer": "",
        "portfolio": [q["question_id"] for q in portfolio],
        "all_scored": [q["question_id"] for q in scored],
        "dissent_portfolio": [q["question_id"] for q in dissent_p],
        "decisions": cards,
    }
    if "scores" in doc or "generated_by" in doc:
        raise AssertionError("review leak")
    atomic_write_yaml(run_dir / "review.yaml", doc)
    return {"status": "awaiting_human", "dissent_referenced": True}


def preflight_close(store: Store, doc: dict, report: dict) -> None:
    if not doc.get("reviewer"):
        raise Blocked("reviewer required")
    if report.get("mode") == "ablation" and any(
        d.get("decision") == "adopt" and not d.get("informational")
        for d in doc["decisions"]
    ):
        raise Blocked("ablation cannot ADOPT")
    for d in doc["decisions"]:
        if d.get("informational"):
            continue
        if d["decision"] == "pending" or not d.get("reason"):
            raise Blocked("pending or empty reason")
    wounded_ids = {
        x["question_id"]
        for x in store.load_dissent(doc["run_id"])
        if x.get("question_id") and (
            x.get("kill_count", 0) > 0
            or any(a.get("result") in {"wound", "kill"} for a in x.get("attacks") or [])
        )
    }
    listed = set(doc.get("dissent_portfolio") or [])
    if wounded_ids and not wounded_ids <= listed:
        raise Blocked("dissent_not_referenced")


def close_review(store: Store, run_dir: Path) -> dict:
    doc = load_yaml(run_dir / "review.yaml")
    report = load_yaml(run_dir / "report.yaml") or {}
    preflight_close(store, doc, report)
    decided = {"adopt": 0, "reject": 0, "defer": 0}
    for d in doc["decisions"]:
        q = store.load_question(d["question_id"])
        domain = (q or {}).get("lineage", {}).get("domain", "")
        if d.get("informational"):
            store.record_decision({
                "ts": now_iso(), "question_id": d["question_id"],
                "decision": "reject", "reason": d.get("reason") or "mechanical_rejected",
                "domain": domain, "run_id": doc["run_id"], "informational": True,
            })
            decided["reject"] += 1
            continue
        if not q:
            raise Blocked(f"missing {d['question_id']}")
        if q["status"] in {"ADOPTED", "REJECTED", "DEFERRED"}:
            continue
        if q["status"] != "REVIEWED":
            q["status"] = "REVIEWED"
            store.write_question(q, actor="human", reviewer_ok=True)
            q = store.load_question(d["question_id"])
        final = {"adopt": "ADOPTED", "reject": "REJECTED", "defer": "DEFERRED"}[d["decision"]]
        q["status"] = final
        q["human_review"] = {
            "status": d["decision"],
            "reviewer": doc["reviewer"],
            "note": d["reason"],
        }
        store.write_question(q, actor="human", reviewer_ok=True)
        store.record_decision({
            "ts": now_iso(), "question_id": d["question_id"],
            "decision": d["decision"], "reason": d["reason"],
            "domain": domain, "run_id": doc["run_id"], "informational": False,
        })
        decided[d["decision"]] += 1
    report["human"] = "closed"
    report["dissent_referenced"] = True
    report["decided"] = decided
    atomic_write_yaml(run_dir / "report.yaml", report)
    return {"status": "closed", "dissent_referenced": True, "decided": decided}
