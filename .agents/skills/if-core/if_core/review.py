from __future__ import annotations

from pathlib import Path

import yaml

from .const import PARETO_AXES
from .schema import validate_obj
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
        # DORMANT is parked, not pending: a question no judge scored, or one
        # whose class is out of scope. There is nothing for a human to decide
        # and `close_review` cannot legally move DORMANT to REVIEWED, so a card
        # here makes the run unclosable. It stays in dissent_portfolio, which
        # is what preflight_close actually requires.
        if q["status"] == "DORMANT":
            continue
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


REVIEW_FIELDS = (
    "question", "question_class", "why_matters", "assumptions", "unknowns",
    "evidence", "falsifier", "minimal_test", "action_plan",
)


def review_packet(store: Store, run_dir: Path) -> dict:
    """What a reviewer LWAR is given: the case, with the provenance removed.

    `open_review` already refuses to let scores or `generated_by` into
    review.yaml, and a reviewer gets the same treatment — no vendor, no
    operator, no machine ranking. Those say who wrote a question and how the
    pipeline ranked it, which is exactly what an independent judgement must not
    lean on. The dissent is included with its verdicts, because an attack that
    already landed is evidence about the question rather than about its author.
    """
    doc = load_yaml(run_dir / "review.yaml")
    items = []
    for d in doc["decisions"]:
        q = store.load_question(d["question_id"]) or {}
        item = {"question_id": d["question_id"]}
        for key in REVIEW_FIELDS:
            if q.get(key):
                item[key] = q[key]
        item["dissent"] = [
            {"dtype": a.get("dtype"), "result": a.get("result"),
             "attack": a.get("attack"), "rationale": a.get("rationale")}
            for a in (q.get("dissent") or [])
        ]
        items.append(item)
    return {"run_id": doc["run_id"], "questions": items}


def apply_recommendation(run_dir: Path, outbox: dict, recommended_by: str) -> dict:
    """Fold a reviewer LWAR's recommendation into review.yaml.

    `reviewer` is deliberately left empty. `preflight_close` refuses a run
    without one, so a recommendation cannot close anything until a person puts
    their name on it — that is the whole guard, and it is why this does not
    simply write `reviewer` itself.
    """
    validate_obj("review_outbox", outbox)
    doc = load_yaml(run_dir / "review.yaml")
    if outbox["run_id"] != doc["run_id"]:
        raise Blocked("recommendation is for %s, not %s"
                      % (outbox["run_id"], doc["run_id"]))
    by_id = {r["question_id"]: r for r in outbox["recommendations"]}
    missing = [d["question_id"] for d in doc["decisions"]
               if not d.get("informational") and d["question_id"] not in by_id]
    if missing:
        raise Blocked("no recommendation for: %s" % ", ".join(missing))
    applied = 0
    for d in doc["decisions"]:
        rec = by_id.get(d["question_id"])
        if rec is None or d.get("informational"):
            continue
        if not (rec.get("reason") or "").strip():
            raise Blocked("empty reason for %s" % d["question_id"])
        d["decision"] = rec["decision"]
        d["reason"] = rec["reason"]
        d["informational"] = bool(rec.get("informational", False))
        if rec.get("checks"):
            d["checks"] = rec["checks"]
        applied += 1
    doc["reviewer_kind"] = "machine_recommended"
    doc["recommended_by"] = recommended_by
    doc["reviewer"] = ""
    validate_obj("review", doc)
    atomic_write_yaml(run_dir / "review.yaml", doc)
    return {"status": "recommended", "applied": applied,
            "recommended_by": recommended_by, "awaiting": "human ratification"}


def ratify(run_dir: Path, reviewer: str) -> dict:
    """A person takes ownership of a machine recommendation."""
    reviewer = (reviewer or "").strip()
    if not reviewer:
        raise Blocked("reviewer required")
    doc = load_yaml(run_dir / "review.yaml")
    if doc.get("reviewer_kind") == "machine_recommended":
        doc["reviewer_kind"] = "human_ratified"
    doc["reviewer"] = reviewer
    validate_obj("review", doc)
    atomic_write_yaml(run_dir / "review.yaml", doc)
    return {"status": "ratified", "reviewer": reviewer,
            "reviewer_kind": doc.get("reviewer_kind")}


def close_review(store: Store, run_dir: Path) -> dict:
    doc = load_yaml(run_dir / "review.yaml")
    report = load_yaml(run_dir / "report.yaml") or {}
    preflight_close(store, doc, report)
    # Stamped on every decision record: a reason feeds the next run's
    # avoid_patterns, so a machine-written one must stay distinguishable from a
    # human's after the fact.
    decided_by = doc.get("reviewer_kind") or "human"
    decided = {"adopt": 0, "reject": 0, "defer": 0}
    for d in doc["decisions"]:
        q = store.load_question(d["question_id"])
        domain = (q or {}).get("lineage", {}).get("domain", "")
        if d.get("informational"):
            store.record_decision({
                "ts": now_iso(), "question_id": d["question_id"],
                "decision": "reject", "reason": d.get("reason") or "mechanical_rejected",
                "domain": domain, "run_id": doc["run_id"], "informational": True,
                "decided_by": decided_by,
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
            "decided_by": decided_by,
        })
        decided[d["decision"]] += 1
    report["human"] = "closed"
    report["reviewer_kind"] = decided_by
    report["dissent_referenced"] = True
    report["decided"] = decided
    atomic_write_yaml(run_dir / "report.yaml", report)
    return {"status": "closed", "dissent_referenced": True, "decided": decided}
