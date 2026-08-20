from __future__ import annotations

from .const import EVIDENCE_KINDS, FAMILY_NORM, OBJECTIVES, OPERATORS
from .store import Blocked


def vendor_family(lwar: dict) -> str:
    raw = lwar.get("vendor_family") or (lwar.get("profile") or {}).get("vendor_family")
    if not raw:
        raise Blocked(f"{lwar.get('lwar_id')} missing vendor_family")
    return FAMILY_NORM.get(str(raw).lower(), str(raw).lower())


def default_ops_for(index: int, k: int = 3) -> list[str]:
    n = len(OPERATORS)
    return [OPERATORS[(index * k + j) % n][0] for j in range(k)]


def leftover_ops(used_keys: set, family: str, ev: str, preferred: list | None = None) -> list[str] | None:
    for shift in range(len(OPERATORS)):
        ops = default_ops_for(shift, 3)
        if preferred and set(preferred) == set(ops):
            continue
        if (family, frozenset(ops), ev) not in used_keys:
            return ops
    return None


def rotate_kind(ev: str) -> str:
    if ev not in EVIDENCE_KINDS:
        return EVIDENCE_KINDS[0]
    return EVIDENCE_KINDS[(EVIDENCE_KINDS.index(ev) + 1) % len(EVIDENCE_KINDS)]


def build_allocation(brief: dict, lwars: list[dict], avoid: list[str] | None = None) -> dict:
    families = {vendor_family(x) for x in lwars}
    if brief.get("mode", "normal") == "normal" and len(families) < 2:
        raise Blocked("need >= 2 vendor_family for normal mode")
    kinds = list(brief.get("evidence_hints") or {}) or list(EVIDENCE_KINDS)
    avoid = list(avoid or [])
    table, used = {}, set()
    for i, lwar in enumerate(lwars):
        fam = vendor_family(lwar)
        ev = kinds[i % len(kinds)]
        ops = default_ops_for(i, 3)
        key = (fam, frozenset(ops), ev)
        if key in used:
            ops = leftover_ops(used, fam, ev, ops)
            if ops is None:
                ev = kinds[(i + 1) % len(kinds)]
                ops = leftover_ops(used, fam, ev, default_ops_for(i + 7, 3))
            if ops is None:
                raise Blocked("cannot satisfy heterogeneity key")
            key = (fam, frozenset(ops), ev)
        used.add(key)
        lid = lwar["lwar_id"]
        table[lid] = {
            "vendor_family": fam,
            "operators": ops,
            "evidence_kind": ev,
            "objective": OBJECTIVES[i % 3],
            # Every slot gets every pattern. Operators, evidence_kind and
            # objective are the diversity knobs; a rejected trap is not one.
            # Striding these across slots left each generator blind to most of
            # them, and RUN-20260819-live4b reproduced exactly the two traps
            # whose reasons had been routed to a different LWAR.
            "avoid_patterns": list(avoid),
            # A standing rule for every generator, unlike avoid_patterns, which
            # is a list of things that already went wrong. The brief has carried
            # this field since the schema was written and nothing ever read it,
            # so an operator could state a constraint, watch the brief validate,
            # and have it silently dropped. RUN-20260820-live6 is what that
            # costs: a question was rejected for demanding a 1e18-1e22 sweep,
            # that reason sat in the avoid window, and the next run asked for
            # 1e24-1e26 anyway. Past examples do not bind; a rule can.
            "constraints": list(brief.get("constraints") or []),
            "hint_strings": (brief.get("evidence_hints") or {}).get(ev, []),
            "max_seeds": brief.get("budget", {}).get("max_seeds_per_lwar", 8),
            "must_consider": (brief.get("must_consider_slices") or {}).get(lid, []),
        }
    return table


def inject_divergence(alloc: dict, brief: dict) -> dict:
    nxt = {k: dict(v) for k, v in alloc.items()}
    used_ops = {op for sl in nxt.values() for op in sl["operators"]}
    unused = [op for op, _ in OPERATORS if op not in used_ops] or [op for op, _ in OPERATORS]
    keys = set()
    for i, sl in enumerate(nxt.values()):
        new_ops = sl["operators"][:]
        new_ops[i % len(new_ops)] = unused[i % len(unused)]
        if not (2 <= len(set(new_ops)) <= 3):
            new_ops = default_ops_for(i + 3, 3)
        sl["operators"] = new_ops
        sl["evidence_kind"] = rotate_kind(sl["evidence_kind"])
        sl["hint_strings"] = (brief.get("evidence_hints") or {}).get(sl["evidence_kind"], [])
        key = (sl["vendor_family"], frozenset(sl["operators"]), sl["evidence_kind"])
        if key in keys:
            raise Blocked("divergence broke heterogeneity")
        keys.add(key)
    return nxt
