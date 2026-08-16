from __future__ import annotations

from .const import FORBIDDEN_SCORE_KEYS
from .gates import distinct_content, first_fail, mechanical_gates
from .schema import SchemaError, validate_obj


def template_restyle(q: dict) -> str:
    return "\n".join([
        "concept: " + ", ".join(q.get("target_concepts") or []),
        "premise: " + "; ".join(q.get("assumptions") or []),
        "unknown: " + "; ".join(q.get("unknowns") or []),
        "falsifier: " + (q.get("falsifier") or ""),
    ])


def blind_packet(q: dict, anon_id: str) -> dict:
    return {
        "anon_id": anon_id,
        "question": template_restyle(q),
        "question_class": q["question_class"],
        "unknown_type": q["unknown_type"],
        "target_concepts": q.get("target_concepts") or [],
        "assumptions": q.get("assumptions") or [],
        "unknowns": q.get("unknowns") or [],
        "evidence_claims": [e["claim"] for e in q.get("evidence") or []],
        "minimal_test": q.get("minimal_test") or {},
        "action_plan": q.get("action_plan") or {},
    }


def judge(inbox: dict) -> list[dict]:
    examiner = inbox.get("lwar_id")
    if examiner and examiner in (inbox.get("exclude_lwars") or []):
        raise PermissionError("excluded judge")
    cards = []
    for b in inbox["questions"]:
        if "question_id" in b or "local_id" in b or "generated_by" in (b.get("lineage") or {}):
            raise PermissionError("blind fields present")
        shape = {
            "target_concepts": b.get("target_concepts"),
            "assumptions": b.get("assumptions"),
            "unknowns": b.get("unknowns"),
            "action_plan": b.get("action_plan"),
            "minimal_test": b.get("minimal_test"),
            "evidence": [{"source": "hidden-src", "claim": c, "confidence": 0.5}
                         for c in b.get("evidence_claims") or []],
        }
        gates = mechanical_gates(shape, ["hidden-src"])
        if any(gates[g] == "fail" for g in ("G-CLEAR", "G-PATH", "G-TESTSHAPE")):
            card = {
                "anon_id": b["anon_id"],
                "verdict": "GATE_FAIL",
                "failed_gate": first_fail(gates),
                "scores": {},
                "notes": "",
            }
        else:
            claims = b.get("evidence_claims") or []
            card = {
                "anon_id": b["anon_id"],
                "verdict": "SCORED",
                "failed_gate": None,
                "scores": {
                    "impact": None,
                    "testability": 0.7,
                    "grounding": min(1.0, len(claims) / 3),
                    "actionability": 1.0 if distinct_content(b.get("action_plan") or {}) else 0.0,
                },
                "notes": "",
            }
        extra = set(card.get("scores") or {}) & FORBIDDEN_SCORE_KEYS
        if extra:
            raise SchemaError("forbidden score keys")
        validate_obj("score_card_outbox", card)
        cards.append(card)
    return cards
