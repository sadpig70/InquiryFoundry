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
import json
import os
import random
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


def _author_identity(lwar_id: str, registry_path=None) -> dict:
    """vendor_family + instance_id for a slot, read at run time.

    Slots get recycled across generations -- LWAR2 has been Grok and GLM,
    LWAR6 Kimi and Grok -- and every scoreboard keyed on slot id needed a
    manual run-era separation, four times. Recording who actually held the
    slot when the run happened makes the ledger self-describing. Fail-safe:
    an unreadable registry records nothing rather than blocking the run.
    """
    path = Path(registry_path or ".pao/var/registry/lwar_registry.json")
    try:
        reg = json.loads(path.read_text(encoding="utf-8"))
        slot = reg["slots"][lwar_id]
        return {"vendor_family": (slot.get("profile") or {}).get("vendor_family"),
                "instance_id": slot.get("instance_id")}
    except (OSError, KeyError, ValueError):
        return {}


def _mint_anon(nonce: bytes, key: str) -> str:
    return "P-" + hmac.new(nonce, key.encode(), hashlib.sha256).hexdigest()[:12]


def has_quant_reject_if(q: dict) -> bool:
    rj = str((q.get("minimal_test") or {}).get("reject_if") or "")
    return any(ch.isdigit() for ch in rj) and len(rj) > 20


def select_batch(store: IfaStore, n: int = 6, mode: str = "fresh") -> list[dict]:
    """fresh: questions never predicted. second-opinion: questions holding
    exactly one REGISTERED prediction -- the 71 singles the first walk left
    when the roster thinned to one strong vendor. A second registered opinion
    is what turns them from unusable into agree/split, and a candidate
    vendor's registration rate on this pass doubles as its qualification
    score: the blind review that flunked 68 straight predictions is the
    hardest honest gate this project owns."""
    adopted = store.read_adopted()
    answers = store.load_answers()
    if mode == "second-opinion":
        reg_count: dict[str, int] = {}
        pending: set[str] = set()
        for a in answers:
            if a["status"] == "REGISTERED":
                reg_count[a["question_id"]] = reg_count.get(a["question_id"], 0) + 1
            elif a["status"] in ("DRAFT", "SCORED"):
                # A prediction is already in flight and unreviewed. Without
                # this exclusion the decoupled phases loop: reviews run after
                # all rounds, so REGISTERED never moves during the walk and
                # every batch re-selects the same head of the singles list --
                # seven batches predicted the same eight questions before this
                # line existed.
                pending.add(a["question_id"])
        singles = {qid for qid, c in reg_count.items() if c == 1} - pending
        quant = [q for q in adopted
                 if q["question_id"] in singles and has_quant_reject_if(q)]
    elif mode == "contested":
        # Requalification exam material once the coverage walk is done: the
        # questions whose registered predictions split. A candidate's take on
        # a contested question is worth more than one more voice in a chorus,
        # and the same run doubles as tie-breaking for the priorities map.
        by_q: dict[str, list] = {}
        pending2: set[str] = set()
        for a in answers:
            if a["status"] == "REGISTERED":
                by_q.setdefault(a["question_id"], []).append(
                    a["prediction"].get("direction"))
            elif a["status"] in ("DRAFT", "SCORED"):
                pending2.add(a["question_id"])
        contested = {qid for qid, dirs in by_q.items()
                     if len(dirs) > 1 and len(set(dirs)) > 1} - pending2
        quant = [q for q in adopted
                 if q["question_id"] in contested and has_quant_reject_if(q)]
    else:
        done = {a["question_id"] for a in answers}
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
                      *, runner=None, registry_path=None) -> dict:
    run_dir = store.run_dir(run_id)
    batch_p = run_dir / "batch.yaml"
    batch = load_yaml(batch_p)
    if not batch:
        raise SystemExit(f"no batch at {batch_p}; run select first")
    # A reused run_id reuses its deterministic task ids and its jail, and a
    # stale outbox from the id's first life then satisfies collection for
    # work nobody did (observed when a driver restarted its numbering).
    jail_root = run_dir / "jail"
    if jail_root.exists() and any(f.is_file() for f in jail_root.rglob("*")):
        raise SystemExit(
            f"{run_id}: jail already holds artifacts -- run ids must not be "
            f"reused; pick a fresh run id")
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
        # Who actually held each slot at run time (slot ids get recycled).
        "authors": {lid: _author_identity(lid, registry_path) for lid in authors},
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

ANCHORS_PER_REVIEW = 3


def pick_anchors(store: IfaStore, run_id: str, k: int = ANCHORS_PER_REVIEW) -> list[dict]:
    """Previously-decided cases to smuggle into a review, for drift measurement.

    The same reviewer registered the same vendor's work at 62.5 percent one
    day and 87.1 the next -- a 24.6-point calibration drift that took a
    dedicated mixed-vendor walk to expose after the fact. Re-judging a few
    already-decided cases inside every review measures it in real time
    instead: the anchors' original verdicts are the baseline, and how many
    flip is the drift. Deterministic per run_id so a rerun picks the same set.
    """
    pool = [a for a in store.load_answers()
            if a["run_id"] != run_id and a.get("review")
            and a["status"] in ("REGISTERED", "DISCARDED")]
    if not pool:
        return []
    rnd = random.Random(run_id)
    regs = [a for a in pool if a["status"] == "REGISTERED"]
    disc = [a for a in pool if a["status"] == "DISCARDED"]
    picks = rnd.sample(regs, min(2, len(regs))) if regs else []
    if disc:
        picks += rnd.sample(disc, min(k - len(picks), len(disc)))
    return picks


def _anchor_alias(run_id: str, answer_id: str) -> str:
    """An id shaped like a real one, so the reviewer cannot tell an anchor."""
    h = hashlib.sha256(f"{run_id}:{answer_id}".encode()).hexdigest()[:10]
    return f"ANS-{h}"


def review_packet(store: IfaStore, run_id: str) -> dict:
    """Provenance-free: no vendor, no machine scores (inherited stance)."""
    answers = store.load_answers(run_id)

    def _case(a, alias=None):
        return {
            "answer_id": alias or a["answer_id"],
            "question_id": a["question_id"],
            "prediction": {k: a["prediction"][k] for k in
                           ("direction", "prediction", "rationale",
                            "confidence", "kill_condition", "evidence")
                           if k in a["prediction"]},
            "rebuttals": a.get("rebuttals") or [],
        }

    items = [_case(a) for a in answers]
    anchors = pick_anchors(store, run_id)
    anchor_map = {}
    for a in anchors:
        alias = _anchor_alias(run_id, a["answer_id"])
        anchor_map[alias] = {"answer_id": a["answer_id"],
                             "original": "register" if a["status"] == "REGISTERED"
                             else "discard"}
        items.append(_case(a, alias))
    if anchor_map:
        atomic_write_yaml(store.run_dir(run_id) / "anchors.yaml", anchor_map)
        random.Random(run_id).shuffle(items)   # anchors must not sit at the end
    return {"contract": roles.REVIEW, "run_id": run_id, "cases": items}


def fold_review(store: IfaStore, run_id: str, outbox_doc, recommended_by: str) -> dict:
    run_dir = store.run_dir(run_id)
    if not isinstance(outbox_doc, list) or not outbox_doc:
        raise SchemaError("review outbox must be a non-empty list")
    known = {a["answer_id"] for a in store.load_answers(run_id)}
    anchor_map = load_yaml(run_dir / "anchors.yaml") or {}
    anchor_report = {"n": len(anchor_map), "judged": 0, "flipped": 0, "details": []}
    decisions = []
    for d in outbox_doc:
        aid = d.get("answer_id")
        if aid in anchor_map:
            ref = anchor_map[aid]
            flipped = d.get("decision") != ref["original"]
            anchor_report["judged"] += 1
            anchor_report["flipped"] += int(flipped)
            anchor_report["details"].append(
                {"original": ref["original"], "now": d.get("decision"),
                 "flipped": flipped})
            continue                       # an anchor never touches the store
        if aid not in known:
            raise SchemaError(f"unknown answer_id {aid}")
        if d.get("decision") not in ("register", "discard"):
            raise SchemaError("decision must be register|discard")
        if not str(d.get("reason") or "").strip():
            raise SchemaError("empty reason")
        decisions.append({"answer_id": d["answer_id"],
                          "decision": d["decision"], "reason": d["reason"]})
    doc = {"run_id": run_id, "recommended_by": recommended_by,
           "reviewer": "",                       # a machine cannot fill this
           "decisions": decisions}
    if anchor_report["n"]:
        anchor_report["drift"] = (round(anchor_report["flipped"] /
                                        anchor_report["judged"], 2)
                                  if anchor_report["judged"] else None)
        doc["anchor_report"] = anchor_report
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


def vendor_scores(store: IfaStore) -> dict[str, dict]:
    """Per-author registration rate, read off the assignment tables.

    The reviewer never sees authorship, so this rate is a blinded quality
    measurement -- the qualification score for candidate vendors and the
    replacement evidence for incumbents.
    """
    import yaml as _yaml
    out: dict[str, dict] = {}
    for a in store.load_answers():
        asg_p = Path(store.root) / "runs" / a["run_id"] / "assignment.yaml"
        if not asg_p.is_file():
            continue
        asg = _yaml.safe_load(asg_p.read_text(encoding="utf-8"))
        author = (asg.get("anon_authors") or {}).get(a.get("anon_id"))
        if not author:
            continue
        # Key on who held the slot, not on the slot: four scoreboards in a
        # row needed manual run-era surgery because slot numbers recycle.
        ident = (asg.get("authors") or {}).get(author) or {}
        fam, inst = ident.get("vendor_family"), ident.get("instance_id") or ""
        key = "%s:%s" % (fam, inst[-8:]) if fam and inst else "%s (legacy-slot)" % author
        row = out.setdefault(key, {"registered": 0, "discarded": 0, "other": 0})
        key = {"REGISTERED": "registered", "DISCARDED": "discarded"}.get(a["status"], "other")
        row[key] += 1
    for row in out.values():
        judged = row["registered"] + row["discarded"]
        row["rate"] = round(row["registered"] / judged, 3) if judged else None
    return out


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
        dirs = [p.get("direction") for p in preds]
        minority = min(dirs.count("reject"), dirs.count("no-reject"))
        out.append({"question_id": qid, "n_registered": len(preds),
                    "directions": dirs,
                    "minority_frac": round(minority / len(dirs), 2) if len(dirs) > 1 else None,
                    "disagreement": disagreement(preds) if len(preds) > 1 else "single"})
    out.sort(key=lambda r: (rank.get(r["disagreement"], 3), -r["n_registered"]))
    return out
