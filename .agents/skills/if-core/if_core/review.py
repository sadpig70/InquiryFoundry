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


def default_reason_kind(decision: str) -> str:
    """A deferral is usually about us; anything else is about the question."""
    return "our_capacity" if decision == "defer" else "question_defect"


REVIEW_FIELDS = (
    "question", "question_class", "why_matters", "assumptions", "unknowns",
    "evidence", "falsifier", "minimal_test", "action_plan",
)


def review_packet(store: Store, run_dir: Path,
                  constraints: list[str] | None = None) -> dict:
    """What a reviewer LWAR is given: the case, with the provenance removed.

    The run's `constraints` travel with it. Without them the reviewer judges
    feasibility in the abstract while the generator was working inside a stated
    envelope, and the two disagree for no better reason than that: calibrating
    against RUN-20260820-live6, the only feasibility split was a question the
    operator deferred for want of cluster access and the reviewer adopted as
    "runnable at accessible scale". Pass `constraints` explicitly to re-review
    an older run under an envelope its own brief never carried.

    `open_review` already refuses to let scores or `generated_by` into
    review.yaml, and a reviewer gets the same treatment — no vendor, no
    operator, no machine ranking. Those say who wrote a question and how the
    pipeline ranked it, which is exactly what an independent judgement must not
    lean on. The dissent is included with its verdicts, because an attack that
    already landed is evidence about the question rather than about its author.
    """
    doc = load_yaml(run_dir / "review.yaml")
    if constraints is None:
        brief = load_yaml(run_dir / "brief.yaml") or {}
        constraints = list(brief.get("constraints") or [])
    # The registry travels with the packet so a reviewer can reuse an existing
    # line for a defect already named. Nothing else keeps the vocabulary from
    # drifting into a list of near-duplicates, which is the failure Fable
    # flagged as the one it could not predict.
    brief = load_yaml(run_dir / "brief.yaml") or {}
    domain = brief.get("domain") or ""
    known = [e["pattern"] for e in store.avoid_registry(domain)] if domain else []
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
    return {"run_id": doc["run_id"], "constraints": list(constraints),
            "known_patterns": known, "questions": items}


def request_review(store: Store, run_dir: Path, lwar_id: str,
                   recommended_by: str, timeout_s: int = 1200,
                   apply: bool = True, constraints: list[str] | None = None,
                   round_n: int | None = None) -> dict:
    """Send one run to a reviewer LWAR and fold back what it recommends.

    The reviewer must not be one of the runtimes that generated the run — the
    independence is the whole point, and `cross_assign` already refuses to let a
    runtime examine its own output in the contrarian and judge phases.
    """
    from .bus import publish_collect

    doc = load_yaml(run_dir / "review.yaml")
    generators = {
        (store.load_question(d["question_id"]) or {})
        .get("lineage", {}).get("generated_by")
        for d in doc["decisions"]
    }
    if lwar_id in generators:
        raise Blocked("%s generated part of this run and cannot review it" % lwar_id)

    if round_n is None:
        # task_id is derived from (run_id, role, lwar, round_n) and the ledger
        # refuses a repeat, so a second review of the same run collides on r0.
        # Re-reviewing is a normal thing to want — a changed envelope, a second
        # opinion — so find the next free round instead of making the operator
        # track it.
        used = {
            int(f.stem.rsplit("-r", 1)[1])
            for f in (run_dir / "pao_drafts").glob("review-%s-r*.json" % lwar_id)
            if f.stem.rsplit("-r", 1)[-1].isdigit()
        }
        round_n = max(used) + 1 if used else 0

    packet = review_packet(store, run_dir, constraints)
    inbox = {
        "schema": "if.task.v1",
        "role": "review",
        "run_id": packet["run_id"],
        "lwar_id": lwar_id,
        "phase": "REVIEW",
        "constraints": packet["constraints"],
        # Reuse one of these when the defect is one already named.
        "known_patterns": packet["known_patterns"],
        "questions": packet["questions"],
        "round_n": round_n,
    }
    accepted, statuses = publish_collect(run_dir, "review", [(lwar_id, inbox)], timeout_s)
    outbox = accepted.get(lwar_id)
    if not outbox:
        raise Blocked("no review returned (%s)" % ", ".join(statuses or ["no status"]))
    if not apply:
        # Calibration against a run a person already decided. Folding the
        # recommendation in would overwrite their verdicts, and comparing the
        # two is the entire point.
        validate_obj("review_outbox", outbox)
        return {"status": "collected", "applied": 0, "recommended_by": recommended_by,
                "round_n": round_n,
                "recommendations": outbox["recommendations"],
                "observed_statuses": statuses}
    result = apply_recommendation(run_dir, outbox, recommended_by)
    result["observed_statuses"] = statuses
    result["round_n"] = round_n
    return result


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
        # Absent means the verdict is about the question. A reviewer that means
        # "we cannot run this" has to say so, because that must not be fed
        # forward as something the next run should avoid asking.
        d["reason_kind"] = rec.get("reason_kind") or default_reason_kind(rec["decision"])
        if rec.get("pattern"):
            d["pattern"] = rec["pattern"].strip()
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


def ratify(run_dir: Path, reviewer: str, delegated: bool = False) -> dict:
    """A person takes ownership of a machine recommendation.

    Two ways to own one, and the log has to tell them apart. `human_ratified`
    means a person read these verdicts and signed them. `delegated` means a
    person authorised a standing delegation and the machine made this
    particular call — still their responsibility, but they did not read it.

    Recording both as the same thing would hide, precisely where it matters,
    which verdicts a human actually looked at. These reasons feed the next
    run's avoid_patterns, and if question quality drifts the first thing worth
    asking is whether it tracks the delegated closes.
    """
    reviewer = (reviewer or "").strip()
    if not reviewer:
        raise Blocked("reviewer required")
    doc = load_yaml(run_dir / "review.yaml")
    if doc.get("reviewer_kind") == "machine_recommended":
        doc["reviewer_kind"] = "delegated" if delegated else "human_ratified"
    doc["reviewer"] = reviewer
    validate_obj("review", doc)
    atomic_write_yaml(run_dir / "review.yaml", doc)
    return {"status": "ratified", "reviewer": reviewer,
            "reviewer_kind": doc.get("reviewer_kind")}


def reopen_review(store: Store, run_dir: Path) -> dict:
    """Put recovered questions back in front of a review that already closed.

    `rejudge` scores questions a lost judge left behind, but a closed run has
    no way to take them: `close_review` skips anything already transitioned and
    overwrites `report.decided`, so the recovered work would sit at SCORED
    forever. Building the recovery and not the way back would repeat the
    mistake it was fixing — DORMANT was a parking space with no exit until
    `rejudge`, and this is that exit's other half.

    Only questions this run minted, now SCORED, and absent from the existing
    decisions are added. Verdicts already made are never touched, and the
    counts already reported stay as they were: `close_review` adds to them.
    """
    doc = load_yaml(run_dir / "review.yaml")
    id_map = load_yaml(run_dir / "local_id_map.yaml") or {}
    listed = {d["question_id"] for d in doc["decisions"]}
    added = []
    for local_id, qid in sorted(id_map.items()):
        if qid in listed:
            continue
        q = store.load_question(qid)
        if not q or q.get("status") != "SCORED":
            continue
        doc["decisions"].append({
            "question_id": qid,
            "question": q["question"],
            "minimal_test": q.get("minimal_test") or {},
            "decision": "pending",
            "reason": "",
            "informational": False,
            "checks": {"already_answered": None, "test_runnable": None, "duplicate": None},
            "bucket": "pareto",
        })
        added.append(qid)
    if not added:
        return {"status": "nothing_to_reopen", "added": []}
    # A fresh verdict is owed on these, so the run is not signed any more.
    doc["reviewer"] = ""
    doc["reviewer_kind"] = "machine_recommended" if doc.get("recommended_by") else "human"
    if not doc.get("recommended_by"):
        doc.pop("reviewer_kind", None)
    validate_obj("review", doc)
    atomic_write_yaml(run_dir / "review.yaml", doc)
    return {"status": "reopened", "added": added, "awaiting": "review then ratify"}


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
                "reason_kind": d.get("reason_kind") or "question_defect",
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
            "reason_kind": d.get("reason_kind") or default_reason_kind(d["decision"]),
            **({"pattern": d["pattern"]} if d.get("pattern") else {}),
        })
        decided[d["decision"]] += 1
    # Publish the derived registry so a person can see what the loop carries.
    domains = {
        (store.load_question(d["question_id"]) or {}).get("lineage", {}).get("domain")
        for d in doc["decisions"]
    }
    for domain in sorted(x for x in domains if x):
        store.write_avoid_registry(domain)
    report["human"] = "closed"
    report["reviewer_kind"] = decided_by
    # A reopened run adds to what it already reported rather than replacing it:
    # the questions decided in the first pass were decided.
    prior = report.get("decided") or {}
    for key in decided:
        decided[key] += int(prior.get(key) or 0)
    report["dissent_referenced"] = True
    report["decided"] = decided
    atomic_write_yaml(run_dir / "report.yaml", report)
    return {"status": "closed", "dissent_referenced": True, "decided": decided}
