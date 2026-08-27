"""Hand-rolled validators for the prediction pipeline (decision A11).

There is no worker-side dispatcher: role contracts travel in the inbox, and
validation happens OA-side after collect. An outbox that fails here is dropped
and recorded, never repaired — fail-safe, same stance as IF's ingest.
"""

from __future__ import annotations

CONFIDENCE = ("low", "medium", "high")
DIRECTIONS = ("reject", "no-reject")


class SchemaError(ValueError):
    pass


def _need(obj: dict, field: str, kind=str):
    v = obj.get(field)
    if v is None or (kind is str and not str(v).strip()):
        raise SchemaError(f"missing {field}")
    if kind is not str and not isinstance(v, kind):
        raise SchemaError(f"{field} must be {kind.__name__}")
    return v


def validate_prediction(p: dict) -> dict:
    """One prediction from a predict outbox."""
    _need(p, "question_id")
    _need(p, "prediction")
    direction = str(_need(p, "direction")).strip()
    if direction not in DIRECTIONS:
        raise SchemaError(f"direction must be one of {DIRECTIONS}, got {direction!r}")
    rationale = str(_need(p, "rationale"))
    if len(rationale) < 60:
        raise SchemaError("rationale too thin (<60 chars)")
    conf = str(_need(p, "confidence")).strip().lower()
    if conf not in CONFIDENCE:
        raise SchemaError(f"confidence must be one of {CONFIDENCE}")
    kill = str(_need(p, "kill_condition"))
    if len(kill) < 20:
        raise SchemaError("kill_condition too thin (<20 chars)")
    ev = _need(p, "evidence", list)
    if not ev:
        raise SchemaError("evidence must cite at least one corpus source")
    return p


def validate_predict_outbox(doc, expected_qids: set[str]) -> list[dict]:
    if not isinstance(doc, list) or not doc:
        raise SchemaError("predict outbox must be a non-empty list")
    seen = set()
    for p in doc:
        validate_prediction(p)
        qid = p["question_id"]
        if qid not in expected_qids:
            raise SchemaError(f"unknown question_id {qid}")
        if qid in seen:
            raise SchemaError(f"duplicate prediction for {qid}")
        seen.add(qid)
    return doc


def validate_rebut_outbox(doc, expected_anon: set[str]) -> list[dict]:
    if not isinstance(doc, list):
        raise SchemaError("rebut outbox must be a list")
    for r in doc:
        anon = str(_need(r, "anon_id"))
        if anon not in expected_anon:
            raise SchemaError(f"unknown anon_id {anon}")
        _need(r, "attack")
        result = str(_need(r, "result")).strip()
        if result not in ("stands", "wounded", "refuted"):
            raise SchemaError("result must be stands|wounded|refuted")
    return doc


def validate_adjudicate_outbox(doc, expected_anon: set[str]) -> list[dict]:
    if not isinstance(doc, list) or not doc:
        raise SchemaError("adjudicate outbox must be a non-empty list")
    for c in doc:
        anon = str(_need(c, "anon_id"))
        if anon not in expected_anon:
            raise SchemaError(f"unknown anon_id {anon}")
        for axis in ("grounding", "consistency", "falsifiability"):
            v = c.get(axis)
            if not isinstance(v, (int, float)) or not 0 <= float(v) <= 1:
                raise SchemaError(f"{axis} must be a number in [0,1]")
        # No novelty axis exists here either -- an LLM scoring novelty of an
        # LLM's prediction is the same trap IF banned (Invariant 4).
        extra = set(c) - {"anon_id", "grounding", "consistency", "falsifiability", "note"}
        if extra:
            raise SchemaError(f"undeclared keys: {sorted(extra)}")
    return doc
