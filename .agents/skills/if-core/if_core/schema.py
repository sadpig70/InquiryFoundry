from __future__ import annotations

from copy import deepcopy

from jsonschema import Draft202012Validator

from .const import (
    ALLOWED_SCORE_KEYS,
    EVIDENCE_KINDS,
    FORBIDDEN_SCORE_KEYS,
    GOALS,
    METHODS,
    OBJECTIVES,
    OPERATOR_IDS,
    Q_STATUSES,
    QUESTION_CLASSES,
    REASON_KINDS,
    REVIEWER_KINDS,
    RUN_MODES,
    UNKNOWN_TYPES,
)


def _str() -> dict:
    return {"type": "string"}


def _nullstr() -> dict:
    return {"type": ["string", "null"]}


def _num_or_null() -> dict:
    return {"type": ["number", "null"]}


EVIDENCE_ITEM = {
    "type": "object",
    "additionalProperties": False,
    "required": ["source", "claim", "confidence"],
    "properties": {
        "source": _str(),
        "claim": _str(),
        "confidence": {"type": "number"},
    },
}

MINIMAL_TEST = {
    "type": "object",
    "additionalProperties": False,
    "required": ["variable", "comparison", "reject_if"],
    "properties": {
        "variable": _str(),
        "comparison": _str(),
        "reject_if": _str(),
    },
}

ACTION_PLAN = {
    "type": "object",
    "additionalProperties": False,
    "required": ["method", "data", "metric", "criterion"],
    "properties": {
        "method": {"enum": METHODS},
        "data": _str(),
        "metric": _str(),
        "criterion": _str(),
    },
}

LINEAGE = {
    "type": "object",
    "additionalProperties": False,
    "required": ["generated_by", "evidence_kind", "objective", "run_id", "parents", "domain"],
    "properties": {
        "generated_by": _str(),
        "evidence_kind": {"enum": EVIDENCE_KINDS},
        "objective": {"enum": OBJECTIVES},
        "run_id": _str(),
        "parents": {"type": "array", "items": _str()},
        "domain": _str(),
    },
}

SCORES = {
    "type": "object",
    "additionalProperties": False,
    "properties": {k: _num_or_null() for k in ALLOWED_SCORE_KEYS},
}

ATTACK = {
    "type": "object",
    "additionalProperties": False,
    "required": ["dtype", "attack", "result", "rationale"],
    "properties": {
        "dtype": _str(),
        "attack": _str(),
        "result": {"enum": ["miss", "wound", "kill"]},
        "rationale": _str(),
        "kill_rule": _nullstr(),
    },
}

HUMAN_REVIEW = {
    "type": "object",
    "additionalProperties": False,
    "required": ["status", "reviewer", "note"],
    "properties": {
        "status": _str(),
        "reviewer": _str(),
        "note": _str(),
    },
}

SEED_PROPS = {
    "local_id": _str(),
    "question_id": _nullstr(),
    "question": _str(),
    "question_norm": _str(),
    "question_class": {"enum": QUESTION_CLASSES},
    "operator": {"enum": OPERATOR_IDS},
    "unknown_type": {"enum": UNKNOWN_TYPES},
    "unknown_ref": _str(),
    "target_concepts": {"type": "array", "items": _str()},
    "why_matters": _str(),
    "assumptions": {"type": "array", "items": _str()},
    "unknowns": {"type": "array", "items": _str()},
    "evidence": {"type": "array", "items": EVIDENCE_ITEM, "minItems": 1},
    "falsifier": _str(),
    "minimal_test": MINIMAL_TEST,
    "action_plan": ACTION_PLAN,
    "lineage": LINEAGE,
}

SCHEMAS: dict[str, dict] = {
    "brief": {
        "type": "object",
        "additionalProperties": False,
        "required": ["brief_id", "domain", "goal", "evidence_hints", "budget"],
        "properties": {
            "brief_id": _str(),
            "mode": {"enum": RUN_MODES},
            "domain": _str(),
            "goal": {"enum": GOALS},
            "constraints": {"type": "array", "items": _str()},
            "forbidden_premises": {"type": "array", "items": _str()},
            "must_consider_slices": {"type": "object", "additionalProperties": {"type": "array", "items": _str()}},
            "success_criteria": _str(),
            "evidence_hints": {
                "type": "object",
                "additionalProperties": {"type": "array", "items": _str()},
                "minProperties": 1,
            },
            "budget": {
                "type": "object",
                "required": ["max_rounds", "max_seeds_per_lwar"],
                "properties": {
                    "max_rounds": {"type": "integer", "minimum": 1},
                    "max_seeds_per_lwar": {"type": "integer", "minimum": 1},
                },
            },
        },
    },
    "seed_outbox": {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "local_id", "question", "question_norm", "question_class", "operator",
            "unknown_type", "unknown_ref", "evidence", "lineage",
        ],
        "properties": SEED_PROPS,
    },
    "qo": {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "local_id", "question_id", "question", "question_norm", "question_class",
            "operator", "unknown_type", "unknown_ref", "evidence", "lineage",
            "version", "status", "contradictions", "estimated_cost", "scores",
            "gate_results", "dissent", "human_review", "created_at", "last_verified_at",
        ],
        "properties": {
            **SEED_PROPS,
            "question_id": _str(),
            "version": {"type": "integer", "minimum": 1},
            "status": {"enum": Q_STATUSES},
            "contradictions": {"type": "array", "items": _str()},
            "estimated_cost": _str(),
            "scores": SCORES,
            "gate_results": {"type": "object"},
            "dissent": {"type": "array"},
            "human_review": HUMAN_REVIEW,
            "created_at": _str(),
            "last_verified_at": _str(),
            "derived_from": {"type": "array", "items": _str()},
        },
    },
    "dissent_report_outbox": {
        "type": "object",
        "additionalProperties": False,
        "required": ["local_id", "examiner", "attacks", "kill_count", "verdict"],
        "properties": {
            "local_id": _str(),
            "examiner": _str(),
            "attacks": {"type": "array", "items": ATTACK, "minItems": 6, "maxItems": 6},
            "kill_count": {"type": "integer", "minimum": 0},
            "verdict": {"enum": ["SURVIVED", "KILLED"]},
        },
    },
    "dissent_report": {
        "type": "object",
        "additionalProperties": False,
        "required": ["local_id", "examiner", "attacks", "kill_count", "verdict", "question_id", "run_id"],
        "properties": {
            "local_id": _str(),
            "examiner": _nullstr(),
            "attacks": {"type": "array", "items": ATTACK},
            "kill_count": {"type": "integer", "minimum": 0},
            "verdict": {"enum": ["SURVIVED", "KILLED"]},
            "question_id": _str(),
            "run_id": _str(),
        },
    },
    "score_card_outbox": {
        "type": "object",
        "additionalProperties": False,
        "required": ["anon_id", "verdict", "scores", "notes"],
        "properties": {
            "anon_id": _str(),
            "verdict": {"enum": ["SCORED", "GATE_FAIL"]},
            "failed_gate": _nullstr(),
            "scores": SCORES,
            "notes": _str(),
        },
    },
    "review_outbox": {
        "type": "object",
        "additionalProperties": False,
        "required": ["run_id", "recommendations"],
        "properties": {
            "run_id": _str(),
            "recommendations": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["question_id", "decision", "reason"],
                    "properties": {
                        "question_id": _str(),
                        "decision": {"enum": ["adopt", "reject", "defer"]},
                        "reason": _str(),
                        "reason_kind": {"enum": REASON_KINDS},
                        "informational": {"type": "boolean"},
                        "checks": {"type": "object"},
                    },
                },
            },
        },
    },
    "review": {
        "type": "object",
        "additionalProperties": False,
        "required": ["run_id", "reviewer", "portfolio", "dissent_portfolio", "decisions"],
        "properties": {
            "run_id": _str(),
            "reviewer": _str(),
            # Who produced the decisions below. Absent means a person wrote
            # them directly; `machine_recommended` means a reviewer LWAR did and
            # nobody has ratified yet.
            "reviewer_kind": {"enum": REVIEWER_KINDS},
            "recommended_by": _str(),
            "portfolio": {"type": "array", "items": _str()},
            "all_scored": {"type": "array", "items": _str()},
            "dissent_portfolio": {"type": "array", "items": _str()},
            "decisions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["question_id", "decision", "reason"],
                    "properties": {
                        "question_id": _str(),
                        "question": _str(),
                        "minimal_test": {},
                        "decision": {"enum": ["adopt", "reject", "defer", "pending"]},
                        "reason": _str(),
                        "reason_kind": {"enum": REASON_KINDS},
                        "informational": {"type": "boolean"},
                        "bucket": {"enum": ["pareto", "dissent", "informational"]},
                        "checks": {"type": "object"},
                    },
                },
            },
        },
    },
    "report": {
        "type": "object",
        "required": ["run_id", "mode", "seed_count", "qo_count"],
        "properties": {
            "run_id": _str(),
            "mode": {"enum": RUN_MODES},
            "separation": {"enum": ["full", "ablation"]},
            "protocol_valid": {"type": "boolean"},
            "hypothesis_valid": {"type": "boolean"},
            "seed_count": {"type": "integer"},
            "qo_count": {"type": "integer"},
            "scored_count": {"type": "integer"},
            "human": _str(),
            "dissent_referenced": {"type": "boolean"},
            "slo_scored_ge_8": {"type": "boolean"},
            "contributing_generate_lwars": {"type": "integer"},
            "observed_statuses": {"type": "array", "items": _str()},
            "decided": {"type": ["object", "null"]},
        },
    },
    "decision_rec": {
        "type": "object",
        "required": ["ts", "question_id", "decision", "reason", "domain", "run_id"],
        "properties": {
            "ts": _str(),
            "question_id": _str(),
            "decision": _str(),
            "reason": _str(),
            "domain": _str(),
            "run_id": _str(),
            "informational": {"type": "boolean"},
            # Provenance of this reason. It feeds the next run's avoid_patterns,
            # so a machine-written reason must stay distinguishable from a
            # human's after the fact.
            "decided_by": {"enum": REVIEWER_KINDS},
            "reason_kind": {"enum": REASON_KINDS},
        },
    },
    "edges_rec": {
        "type": "object",
        "required": ["ts", "src", "rel", "dst"],
        "properties": {
            "ts": _str(),
            "src": _str(),
            "rel": {"enum": ["parent", "derived_from", "contradicts"]},
            "dst": _str(),
        },
    },
}


class SchemaError(ValueError):
    pass


def validate_obj(kind: str, data: dict) -> None:
    if kind not in SCHEMAS:
        raise SchemaError(f"unknown schema kind: {kind}")
    validator = Draft202012Validator(SCHEMAS[kind])
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
    if errors:
        msgs = [f"{'/'.join(str(p) for p in e.path) or '<root>'}: {e.message}" for e in errors]
        raise SchemaError("; ".join(msgs))
    _extra_rules(kind, data)


def _extra_rules(kind: str, data: dict) -> None:
    if kind in {"qo", "score_card_outbox", "seed_outbox"}:
        scores = data.get("scores") or {}
        bad = set(scores) & FORBIDDEN_SCORE_KEYS
        if bad:
            raise SchemaError(f"forbidden score keys: {sorted(bad)}")
    if kind == "score_card_outbox" and "question_id" in data:
        raise SchemaError("judge outbox must not contain question_id")
    if kind == "dissent_report_outbox" and "question_id" in data:
        raise SchemaError("contrarian outbox must not contain question_id")
    if kind == "seed_outbox" and data.get("question_id"):
        raise SchemaError("worker seed must not mint question_id")


def dump_schema(kind: str) -> dict:
    return deepcopy(SCHEMAS[kind])
