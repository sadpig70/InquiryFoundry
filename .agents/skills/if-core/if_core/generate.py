from __future__ import annotations

import re
from pathlib import Path

from .const import MVP_UNKNOWN, NEGATION_CUES, OPERATORS
from .gates import mechanical_ok_shape
from .textutil import normalize_tokens


def extract_claim_lines(hint_files: list[Path]) -> list[dict]:
    claims = []
    for fp in hint_files:
        text = fp.read_text(encoding="utf-8")
        i = 0
        for raw in text.splitlines():
            line = raw.strip().lstrip("-*").strip()
            if not line:
                continue
            i += 1
            source = None
            m = re.search(r"source:\s*(\S+)", line, flags=re.I)
            if m:
                source = m.group(1)
                line = (line[: m.start()] + line[m.end() :]).strip()
            claims.append({
                "claim_id": f"H-{fp.name}-{i}",
                "text": line,
                "source": source,
            })
    return claims


def contradictory_pairs(claims: list[dict]) -> list[tuple[dict, dict]]:
    pairs = []
    for i, a in enumerate(claims):
        for b in claims[i + 1 :]:
            ta, tb = a["text"].lower(), b["text"].lower()
            a_neg = any(c in ta for c in NEGATION_CUES)
            b_neg = any(c in tb for c in NEGATION_CUES)
            if a_neg == b_neg:
                continue
            wa, wb = set(normalize_tokens(a["text"]).split()), set(normalize_tokens(b["text"]).split())
            if wa and wb and jaccard_safe(wa, wb) >= 0.25:
                pairs.append((a, b))
    return pairs


def jaccard_safe(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


def make_u(run_id: str, n: int, typ: str, claim: dict, extra=None) -> dict:
    ids = [claim["claim_id"]] + ([extra["claim_id"]] if extra else [])
    return {
        "id": f"U-{run_id}-{n}",
        "unknown_type": typ,
        "statement": claim["text"] if extra is None else f"{claim['text']} vs {extra['text']}",
        "claim_ids": ids,
        "source_hint": claim.get("source") or (extra.get("source") if extra else None),
        "claims": [claim] + ([extra] if extra else []),
    }


def mine_min(hint_files: list[Path], run_id: str) -> list[dict]:
    claims = extract_claim_lines(hint_files)
    out, n = [], 0
    for c in claims:
        if not c.get("source"):
            n += 1
            out.append(make_u(run_id, n, "known_unknown", c))
    for a, b in contradictory_pairs(claims):
        n += 1
        out.append(make_u(run_id, n, "contradictory", a, extra=b))
    return [u for u in out if u["claim_ids"] and u["unknown_type"] in MVP_UNKNOWN]


def apply_operator(unknown: dict, op: str, objective: str) -> dict | None:
    tmpl = dict(OPERATORS).get(op)
    if not tmpl:
        return None
    q = f"{tmpl} — {unknown['statement']}"
    evidence = []
    for c in unknown.get("claims") or []:
        if c.get("source"):
            evidence.append({"source": c["source"], "claim": c["text"], "confidence": 0.6})
    if not evidence:
        return None
    tests = {
        "OP-CONTRA": ("pair_consistency", "both claims jointly true", "no residual contradiction"),
        "OP-INVERT": ("assumption_hold", "core premise false", "prediction unchanged"),
        "OP-BOUND": ("regime_edge", "stated bound crossed", "relation still holds"),
        "OP-SCALE": ("scale_factor", "compute * 1000", "no new phenomenon"),
        "OP-XDOM": ("foreign_principle", "imported mechanism fits", "no transferable mechanism"),
        "OP-MISSVAR": ("omitted_variable", "candidate covariate", "explained variance unchanged"),
        "OP-CAUSAL": ("intervention", "do(X) changes Y", "association only"),
        "OP-MEASURE": ("instrument", "alt operationalization", "same rank order"),
        "OP-CF": ("counterfactual", "remove A", "B still occurs"),
        "OP-2ND": ("spillover", "success side-effect", "no second-order change"),
        "OP-ADV": ("cheap_break", "lowest-cost attack", "system still holds"),
        "OP-REGIME": ("env_shift", "environment flip", "rule does not reverse"),
    }
    var, cmp_, rej = tests.get(op, ("source_agreement", "pair resolution", "no residual contradiction"))
    return {
        "question": q,
        "question_class": "cause" if op in {"OP-CAUSAL", "OP-CF"} else "phenomenon",
        "target_concepts": [unknown["statement"][:80]],
        "why_matters": f"objective={objective}",
        "assumptions": ["hint claims are correctly extracted"],
        "unknowns": [unknown["statement"]],
        "evidence": evidence,
        "falsifier": f"If all cited sources are withdrawn, '{unknown['statement']}' is vacated.",
        "minimal_test": {
            "variable": var,
            "comparison": cmp_,
            "reject_if": rej,
        },
        "action_plan": {
            "method": "data",
            "data": "hint pack + cited sources",
            "metric": var,
            "criterion": rej,
        },
    }


def fill_seed(local_id: str, raw: dict, u: dict, op: str, sl: dict, inbox: dict) -> dict:
    return {
        "local_id": local_id,
        "question_id": None,
        "question": raw["question"],
        "question_norm": "",
        "question_class": raw["question_class"],
        "operator": op,
        "unknown_type": u["unknown_type"],
        "unknown_ref": u["id"],
        "target_concepts": raw.get("target_concepts") or [],
        "why_matters": raw.get("why_matters") or "",
        "assumptions": raw.get("assumptions") or [],
        "unknowns": raw.get("unknowns") or [u["statement"]],
        "evidence": raw["evidence"],
        "falsifier": raw.get("falsifier") or "",
        "minimal_test": raw.get("minimal_test") or {},
        "action_plan": raw.get("action_plan") or {},
        "lineage": {
            "generated_by": inbox["lwar_id"],
            "evidence_kind": sl["evidence_kind"],
            "objective": sl["objective"],
            "run_id": inbox["run_id"],
            "parents": [],
            "domain": inbox["domain"],
        },
    }


def generate(inbox: dict, hint_dir: Path | None = None) -> list[dict]:
    sl = inbox["allocation_slice"]
    lwar_id = inbox.get("lwar_id") or sl.get("lwar_id") or "LWAR?"
    inbox = {**inbox, "lwar_id": lwar_id}
    root = hint_dir or Path("hints")
    files = sorted(root.glob("**/*")) if root.is_dir() else []
    files = [p for p in files if p.is_file()]
    unknowns = mine_min(files, inbox["run_id"])
    seeds, seq = [], 0
    hints = sl.get("hint_strings") or []
    for u in unknowns:
        for op in sl["operators"]:
            raw = apply_operator(u, op, sl["objective"])
            if raw is None or not raw.get("evidence"):
                continue
            seq += 1
            seed = fill_seed(f"{lwar_id}-{seq:02d}", raw, u, op, sl, inbox)
            seed["question_norm"] = normalize_tokens(seed["question"])
            if seed["question_class"] in {"normative", "meta"}:
                continue
            if not mechanical_ok_shape(seed, hints):
                continue
            seeds.append(seed)
            if len(seeds) >= sl.get("max_seeds", 8):
                return seeds
    return seeds
