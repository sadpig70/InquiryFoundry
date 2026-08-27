"""The prediction pipeline: select → predict → rebut → adjudicate → compose →
review → close.

Inherited invariants, re-enforced here rather than assumed: predictions are
mutually invisible until composed; the rotation table makes self-rebuttal and
self-adjudication impossible and is written to the run dir so the guarantee is
auditable, not asserted; anon ids are minted with a per-run nonce; REGISTERED
exists only downstream of a non-empty reviewer plus ratification.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from pathlib import Path

from . import roles
from .bus import publish_collect
from .schema import (
    SchemaError,
    validate_adjudicate_outbox,
    validate_predict_outbox,
    validate_rebut_outbox,
)
from .store import IfaStore, atomic_write_yaml, load_yaml, now_iso

QUESTION_FIELDS = ("question_id", "question", "why_matters", "assumptions",
                   "falsifier", "minimal_test", "action_plan", "evidence")


def _mint_anon(nonce: bytes, key: str) -> str:
    return "P-" + hmac.new(nonce, key.encode(), hashlib.sha256).hexdigest()[:12]


def has_quant_reject_if(q: dict) -> bool:
    rj = str((q.get("minimal_test") or {}).get("reject_if") or "")
    return any(ch.isdigit() for ch in rj) and len(rj) > 20


def select_batch(store: IfaStore, n: int = 6) -> list[dict]:
    """Quantitative reject_if first, domains interleaved, already-predicted
    questions excluded -- successive runs walk the portfolio instead of
    re-predicting the same head of the list."""
    adopted = store.read_adopted()
    done = {a["question_id"] for a in store.load_answers()}
    quant = [q for q in adopted
             if has_quant_reject_if(q) and q["question_id"] not in done]
    by_domain: dict[str, list] = {}
    for q in quant:
        by_domain.setdefault((q.get("lineage") or {}).get("domain") or "?", []).append(q)
    batch: list[dict] = []
    while len(batch) < n and any(by_domain.values()):
        for dom in sorted(by_domain):
            if by_domain[dom] and len(batch) < n:
                batch.append(by_domain[dom].pop(0))
    return batch


def _question_view(q: dict) -> dict:
    """What a predictor sees: the question, nothing about its lineage."""
    return {k: q[k] for k in QUESTION_FIELDS if q.get(k) is not None}


def run_predict_round(store: IfaStore, run_id: str, lwars: list[str],
                      *, runner=None) -> dict:
    run_dir = store.run_dir(run_id)
    batch_p = run_dir / "batch.yaml"
    batch = load_yaml(batch_p)
    if not batch:
        raise SystemExit(f"no batch at {batch_p}; run select first")
    qids = {q["question_id"] for q in batch}
    nonce = secrets.token_bytes(32)
    (run_dir / "run_nonce").write_bytes(nonce)

    # ---- predict: every vendor, every question, mutually invisible ----
    inbox = {"contract": roles.PREDICT,
             "questions": [_question_view(q) for q in batch]}
    items = [(lid, inbox) for lid in lwars]
    outboxes, statuses = publish_collect(run_dir, "predict", items, runner=runner)
    predictions: dict[str, list[dict]] = {}
    dropped: list[dict] = []
    for lid in lwars:
        doc = outboxes.get(lid)
        try:
            predictions[lid] = validate_predict_outbox(doc, qids)
        except SchemaError as e:
            dropped.append({"lwar_id": lid, "role": "predict", "error": str(e)})
    if len(predictions) < 2:
        report = {"run_id": run_id, "status": "failed",
                  "reason": "fewer than two valid predict outboxes",
                  "dropped": dropped, "statuses": statuses}
        atomic_write_yaml(run_dir / "report.yaml", report)
        return report

    # ---- anon minting + rotation table (auditable, decision in DESIGN) ----
    anon: dict[str, dict] = {}   # anon_id -> {author, question_id, body}
    for lid, preds in predictions.items():
        for p in preds:
            aid = _mint_anon(nonce, f"{lid}:{p['question_id']}")
            anon[aid] = {"author": lid, "question_id": p["question_id"], "body": p}
    authors = sorted(predictions)
    rotation = {
        "rebut": {authors[i]: authors[(i + 1) % len(authors)] for i in range(len(authors))},
        "adjudicate": {authors[i]: authors[(i + 2) % len(authors)] if len(authors) > 2
                       else authors[(i + 1) % len(authors)] for i in range(len(authors))},
    }
    atomic_write_yaml(run_dir / "assignment.yaml", {
        "rotation": rotation,
        "anon_authors": {aid: v["author"] for aid, v in anon.items()},
    })

    def _anon_view(aid: str) -> dict:
        body = dict(anon[aid]["body"])
        return {"anon_id": aid, **{k: body[k] for k in
                ("question_id", "direction", "prediction", "rationale",
                 "confidence", "kill_condition", "evidence") if k in body}}

    def _targets(stage: str, examiner: str) -> list[str]:
        src = rotation[stage][examiner]
        return [aid for aid, v in anon.items() if v["author"] == src]

    # ---- rebut ----
    items = []
    for lid in authors:
        targets = _targets("rebut", lid)
        items.append((lid, {"contract": roles.REBUT,
                            "predictions": [_anon_view(a) for a in targets]}))
    outboxes, st2 = publish_collect(run_dir, "rebut", items, runner=runner)
    statuses += st2
    rebuttals: dict[str, list[dict]] = {}
    for lid in authors:
        expected = set(_targets("rebut", lid))
        try:
            for r in validate_rebut_outbox(outboxes.get(lid) or [], expected):
                if anon[r["anon_id"]]["author"] == lid:
                    raise SchemaError("self-rebuttal")  # unreachable by rotation; belt+braces
                rebuttals.setdefault(r["anon_id"], []).append(
                    {"attack": r["attack"], "result": r["result"]})
        except SchemaError as e:
            dropped.append({"lwar_id": lid, "role": "rebut", "error": str(e)})

    # ---- adjudicate ----
    items = []
    for lid in authors:
        targets = _targets("adjudicate", lid)
        items.append((lid, {
            "contract": roles.ADJUDICATE,
            "cases": [{**_anon_view(a), "rebuttals": rebuttals.get(a, [])}
                      for a in targets]}))
    outboxes, st3 = publish_collect(run_dir, "adjudicate", items, runner=runner)
    statuses += st3
    scores: dict[str, dict] = {}
    for lid in authors:
        expected = set(_targets("adjudicate", lid))
        try:
            for c in validate_adjudicate_outbox(outboxes.get(lid) or [], expected):
                if anon[c["anon_id"]]["author"] == lid:
                    raise SchemaError("self-adjudication")
                scores[c["anon_id"]] = {k: float(c[k]) for k in
                                        ("grounding", "consistency", "falsifiability")}
        except SchemaError as e:
            dropped.append({"lwar_id": lid, "role": "adjudicate", "error": str(e)})

    # ---- compose AnswerObjects: DRAFT then SCORED in one pass ----
    composed = []
    seq = 0
    for aid, v in sorted(anon.items()):
        seq += 1
        ans = {
            "answer_id": f"ANS-{run_id[-6:]}-{seq:03d}",
            "kind": "predicted",                      # the only legal value (A3)
            "status": "SCORED" if aid in scores else "DRAFT",
            "run_id": run_id,
            "question_id": v["question_id"],          # one-way reference (A4)
            "anon_id": aid,
            "prediction": v["body"],
            "rebuttals": rebuttals.get(aid, []),
            "scores": scores.get(aid),
            "created_at": now_iso(),
        }
        store.write_answer(ans)
        composed.append(ans["answer_id"])

    report = {
        "run_id": run_id, "status": "predicted",
        "questions": len(batch), "vendors": authors,
        "answers": composed, "dropped": dropped, "statuses": statuses,
        "human": "awaiting_review",
    }
    atomic_write_yaml(run_dir / "report.yaml", report)
    return report


# ---------------- review / ratify / close ----------------

def review_packet(store: IfaStore, run_id: str) -> dict:
    """Provenance-free: no vendor, no machine scores (inherited stance)."""
    answers = store.load_answers(run_id)
    items = []
    for a in answers:
        items.append({
            "answer_id": a["answer_id"],
            "question_id": a["question_id"],
            "prediction": {k: a["prediction"][k] for k in
                           ("direction", "prediction", "rationale",
                            "confidence", "kill_condition", "evidence")
                           if k in a["prediction"]},
            "rebuttals": a.get("rebuttals") or [],
        })
    return {"contract": roles.REVIEW, "run_id": run_id, "cases": items}


def fold_review(store: IfaStore, run_id: str, outbox_doc, recommended_by: str) -> dict:
    run_dir = store.run_dir(run_id)
    if not isinstance(outbox_doc, list) or not outbox_doc:
        raise SchemaError("review outbox must be a non-empty list")
    known = {a["answer_id"] for a in store.load_answers(run_id)}
    decisions = []
    for d in outbox_doc:
        if d.get("answer_id") not in known:
            raise SchemaError(f"unknown answer_id {d.get('answer_id')}")
        if d.get("decision") not in ("register", "discard"):
            raise SchemaError("decision must be register|discard")
        if not str(d.get("reason") or "").strip():
            raise SchemaError("empty reason")
        decisions.append({"answer_id": d["answer_id"],
                          "decision": d["decision"], "reason": d["reason"]})
    doc = {"run_id": run_id, "recommended_by": recommended_by,
           "reviewer": "",                       # a machine cannot fill this
           "decisions": decisions}
    atomic_write_yaml(run_dir / "review.yaml", doc)
    return doc


def ratify(store: IfaStore, run_id: str, reviewer: str, delegated: bool) -> dict:
    run_dir = store.run_dir(run_id)
    doc = load_yaml(run_dir / "review.yaml")
    if not doc:
        raise SystemExit("no review to ratify")
    doc["reviewer"] = reviewer
    doc["reviewer_kind"] = "delegated" if delegated else "human"
    atomic_write_yaml(run_dir / "review.yaml", doc)
    return doc


def preflight_close(doc: dict) -> None:
    if not doc.get("reviewer"):
        raise PermissionError("reviewer required")   # Invariant 3


def close_run(store: IfaStore, run_id: str) -> dict:
    run_dir = store.run_dir(run_id)
    doc = load_yaml(run_dir / "review.yaml")
    if not doc:
        raise SystemExit("no review.yaml")
    preflight_close(doc)
    counts = {"register": 0, "discard": 0}
    for d in doc["decisions"]:
        a = store.load_answer(d["answer_id"])
        if not a:
            continue
        a["status"] = "REGISTERED" if d["decision"] == "register" else "DISCARDED"
        a["review"] = {"decision": d["decision"], "reason": d["reason"],
                       "reviewer": doc["reviewer"],
                       "reviewer_kind": doc.get("reviewer_kind")}
        store.write_answer(a)
        counts[d["decision"]] += 1
    report = load_yaml(run_dir / "report.yaml") or {}
    report["human"] = "closed"
    report["decided"] = counts
    atomic_write_yaml(run_dir / "report.yaml", report)
    return {"status": "closed", "decided": counts}


# ---------------- the deliverable: disagreement priorities ----------------

def disagreement(preds: list[dict]) -> str:
    """agree | split. With a binary direction a three-way "diverge" cannot
    exist; the design's third level waits for scalar predictions, and faking
    it now would rank noise."""
    dirs = [p.get("direction") for p in preds]
    return "agree" if len(set(dirs)) == 1 else "split"


def priorities(store: IfaStore, run_id: str | None) -> list[dict]:
    """Per-question disagreement over REGISTERED predictions. diverge first --
    where well-grounded models split, a real experiment buys the most."""
    rows: dict[str, list[dict]] = {}
    for a in store.load_answers(run_id):
        if a.get("status") == "REGISTERED":
            rows.setdefault(a["question_id"], []).append(a["prediction"])
    rank = {"split": 0, "agree": 1}
    out = []
    for qid, preds in rows.items():
        out.append({"question_id": qid, "n_registered": len(preds),
                    "directions": [p.get("direction") for p in preds],
                    "disagreement": disagreement(preds) if len(preds) > 1 else "single"})
    out.sort(key=lambda r: (rank.get(r["disagreement"], 3), -r["n_registered"]))
    return out
