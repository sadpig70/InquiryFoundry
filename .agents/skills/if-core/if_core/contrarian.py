from __future__ import annotations

from .const import DISSENT_TYPES
from .schema import validate_obj
from .textutil import normalize_tokens


def evidence_broken(q: dict) -> bool:
    ev = q.get("evidence") or []
    if not ev:
        return True
    unknowns = [normalize_tokens(u) for u in (q.get("unknowns") or []) if u]
    if not unknowns:
        return False
    return all(normalize_tokens(e.get("claim", "")) in unknowns for e in ev)


def premise_forbidden(q: dict, forbidden: list[str]) -> bool:
    blob = " ".join(q.get("assumptions") or [])
    return any(p and p in blob for p in forbidden)


def cross_examine(inbox: dict) -> list[dict]:
    forbidden = inbox.get("forbidden_premises") or []
    examiner = inbox.get("lwar_id") or "LWAR?"
    reports = []
    for q in inbox["questions"]:
        gen = (q.get("lineage") or {}).get("generated_by")
        if gen and gen == examiner:
            raise PermissionError("self-examine")
        attacks = []
        for dtype in DISSENT_TYPES:
            if dtype == "evidence" and evidence_broken(q):
                res, rule, text = "kill", "evidence", "evidence restates unknown or is empty"
            elif dtype == "premise" and premise_forbidden(q, forbidden):
                res, rule, text = "kill", "premise", "assumption matches forbidden_premises"
            else:
                res, rule, text = "miss", None, f"{dtype} attack (deterministic stub)"
            attacks.append({
                "dtype": dtype,
                "attack": text,
                "result": res,
                "rationale": text,
                "kill_rule": rule,
            })
        kills = sum(1 for a in attacks if a["result"] == "kill")
        rec = {
            "local_id": q["local_id"],
            "examiner": examiner,
            "attacks": attacks,
            "kill_count": kills,
            "verdict": "KILLED" if kills >= 1 else "SURVIVED",
        }
        validate_obj("dissent_report_outbox", rec)
        reports.append(rec)
    return reports
