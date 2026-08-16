from __future__ import annotations

from .const import HUMAN, MECH, METHODS


def source_in_hints(source: str, hints: list[str]) -> bool:
    return any(h and len(h) >= 6 and (h in source or source in h) for h in hints)


def distinct_content(plan: dict) -> bool:
    vals = [plan.get(k, "") for k in ("method", "data", "metric", "criterion")]
    return len(set(vals)) == 4 and all(len(str(v)) >= 4 for v in vals)


def mechanical_gates(seed: dict, hints: list[str]) -> dict[str, str]:
    r: dict[str, str] = {}
    ev = seed.get("evidence") or []
    r["G-GROUND"] = (
        "pass"
        if ev and all(
            e.get("source") and e.get("claim") and source_in_hints(str(e["source"]), hints)
            for e in ev
        )
        else "fail"
    )
    plan = seed.get("action_plan") or {}
    r["G-PATH"] = "pass" if plan.get("method") in METHODS else "fail"
    if r["G-PATH"] == "pass" and not distinct_content(plan):
        r["G-PATH"] = "fail"
    mt = seed.get("minimal_test") or {}
    r["G-TESTSHAPE"] = (
        "pass" if all(mt.get(k) for k in ("variable", "comparison", "reject_if")) else "fail"
    )
    filled = bool(seed.get("target_concepts") and seed.get("assumptions") and seed.get("unknowns"))
    r["G-CLEAR"] = "pass" if filled else "fail"
    for g in HUMAN:
        r[g] = "human"
    return r


def mechanical_ok_shape(seed: dict, hints: list[str]) -> bool:
    g = mechanical_gates(seed, hints)
    return all(g[k] == "pass" for k in MECH)


def first_fail(gates: dict[str, str]) -> str | None:
    for k in MECH:
        if gates.get(k) == "fail":
            return k
    return None
