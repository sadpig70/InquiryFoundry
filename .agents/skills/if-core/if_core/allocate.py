from __future__ import annotations

import hashlib

from .const import EVIDENCE_KINDS, FAMILY_NORM, OBJECTIVES, OPERATORS
from .store import Blocked


def vendor_family(lwar: dict) -> str:
    raw = lwar.get("vendor_family") or (lwar.get("profile") or {}).get("vendor_family")
    if not raw:
        raise Blocked(f"{lwar.get('lwar_id')} missing vendor_family")
    return FAMILY_NORM.get(str(raw).lower(), str(raw).lower())


def default_ops_for(index: int, k: int = 3, offset: int = 0) -> list[str]:
    n = len(OPERATORS)
    return [OPERATORS[(index * k + j + offset) % n][0] for j in range(k)]


def run_operator_offset(brief: dict) -> int:
    """Rotate which operators a slot receives, per run.

    Slot i always got operators i*k..i*k+k-1, so the same roster order handed
    the same operator to the same vendor in every run. RUN-20260821-live8
    repeated RUN-20260820-live7b's brief and one runtime returned three
    questions with a token-set Jaccard of 1.00 — a deterministic generator
    given byte-identical input, which is not a fault in the generator.

    Every slot shifts by the same amount, so the triples stay disjoint and the
    heterogeneity key still holds. Derived from brief_id with a stable digest
    (not hash(), which is salted per process), so a run is reproducible.
    """
    brief_id = str(brief.get("brief_id") or "")
    if not brief_id:
        return 0
    digest = hashlib.sha256(brief_id.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") % len(OPERATORS)


def run_objective_offset(brief: dict) -> int:
    """Rotate which objective a slot receives, per run.

    `run_operator_offset` fixed this for operators after live8 and left the
    objective on `OBJECTIVES[i % 3]`, so slot 3 drew `info_per_cost` for six
    consecutive `preference` runs. Six of the seven DUP-RESUBMIT rejects came
    from that slot, and in live17 and live18 every question it produced was
    rejected for it while the other two slots went six for six — which is what
    a question whose answer a larger adopted design already yields looks like
    when the objective rewards cheap information.

    Whether the objective causes that or merely meets a saturating question
    space first is not known, and rotating is the only way to tell: if it is
    the objective the defect follows the knob, and if it is saturation it
    follows whoever holds `info_per_cost`.

    Derived from a different slice of the same digest than the operator
    offset, so the two knobs move independently — sharing one would make them
    inseparable again, in a different way.
    """
    brief_id = str(brief.get("brief_id") or "")
    if not brief_id:
        return 0
    digest = hashlib.sha256(brief_id.encode("utf-8")).digest()
    return int.from_bytes(digest[4:8], "big") % len(OBJECTIVES)


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


def build_allocation(brief: dict, lwars: list[dict], avoid=None) -> dict:
    """`avoid` is `{patterns, recent_reasons}`; a bare list is read as reasons."""
    families = {vendor_family(x) for x in lwars}
    if brief.get("mode", "normal") == "normal" and len(families) < 2:
        raise Blocked("need >= 2 vendor_family for normal mode")
    kinds = list(brief.get("evidence_hints") or {}) or list(EVIDENCE_KINDS)
    if isinstance(avoid, dict):
        patterns = list(avoid.get("patterns") or [])
        restored = list(avoid.get("restored_patterns") or [])
        avoid = list(avoid.get("recent_reasons") or [])
    else:
        patterns, avoid, restored = [], list(avoid or []), []
    # Withheld by default since Fable's second taxonomy decision (2026-08-23).
    # Five runs measured generator-side delivery and found no contribution:
    # RUN-20260822-live16 produced three questions carrying exactly the defect
    # whose code its generators had been handed for two runs, and
    # RUN-20260823-live18 withdrew all eight codes without anything getting
    # worse. The only metric that moved at all moved against delivery — cited
    # sources recovered from 7 to 9 once the codes stopped going out. So the
    # codes stay a reviewer's ledger, and what reaches a generator is rules
    # (`constraints`) and the verbatim window, which is where the one verified
    # win came from: a code names a defect, recurrence enters it in the
    # registry, and that forces a constraint that actually binds.
    #
    # Set `withhold_avoid_codes: false` to deliver them — targeted restoration
    # is the pre-registered response if a registered defect survives its
    # constraint. Only the generator side is affected either way: the reviewer
    # keeps `known_patterns` and `require_known_code`, which lowering
    # `ratified` would not (see 7.25).
    withheld = bool(brief.get("withhold_avoid_codes", True))
    if withheld:
        # Targeted restoration survives the withhold: a code that met its
        # threshold despite a clause is re-delivered alone, everything else
        # stays a reviewer's ledger.
        patterns = restored
    offset = run_operator_offset(brief)
    obj_offset = run_objective_offset(brief)
    table, used = {}, set()
    for i, lwar in enumerate(lwars):
        fam = vendor_family(lwar)
        ev = kinds[i % len(kinds)]
        ops = default_ops_for(i, 3, offset)
        key = (fam, frozenset(ops), ev)
        if key in used:
            ops = leftover_ops(used, fam, ev, ops)
            if ops is None:
                ev = kinds[(i + 1) % len(kinds)]
                ops = leftover_ops(used, fam, ev, default_ops_for(i + 7, 3, offset))
            if ops is None:
                raise Blocked("cannot satisfy heterogeneity key")
            key = (fam, frozenset(ops), ev)
        used.add(key)
        lid = lwar["lwar_id"]
        table[lid] = {
            "vendor_family": fam,
            "operators": ops,
            "evidence_kind": ev,
            "objective": OBJECTIVES[(i + obj_offset) % len(OBJECTIVES)],
            # Every slot gets every pattern. Operators, evidence_kind and
            # objective are the diversity knobs; a rejected trap is not one.
            # Striding these across slots left each generator blind to most of
            # them, and RUN-20260819-live4b reproduced exactly the two traps
            # whose reasons had been routed to a different LWAR.
            "avoid_patterns": list(avoid),
            # Recurring traps, abstracted to their structure. Persist across
            # runs where the verbatim reasons above do not.
            "avoid_registry": list(patterns),
            # Recorded even when false, because an empty `avoid_registry` is
            # ambiguous in the record: withheld on purpose, or nothing to send.
            # RUN-20260821-live8 cost a wrong conclusion to exactly that kind of
            # ambiguity (§7.24) — the run looked fed and was not. A reader of
            # allocation.yaml should never have to infer which arm a run was in.
            "avoid_codes_withheld": withheld,
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
