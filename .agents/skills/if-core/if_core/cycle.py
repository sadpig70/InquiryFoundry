from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from dataclasses import dataclass, field
from pathlib import Path

from .allocate import build_allocation, inject_divergence, vendor_family
from .bus import ensure_jail, publish_collect
from .compose import compose, stamp_lineage
from .const import EXCLUDE_ADAPTERS, EXCLUDE_FAMILIES, PRIOR_N, TH_MEAN, TH_PAIR
from .schema import SchemaError, validate_obj
from .contrarian import cross_examine
from .generate import generate
from .judge import blind_packet, judge
from .review import close_review, open_review
from .store import Blocked, Drop, Store, atomic_write_yaml, load_yaml
from .textutil import jaccard, token_set


@dataclass
class Run:
    id: str
    dir: Path
    brief: dict
    nonce: bytes
    observed_statuses: list[str] = field(default_factory=list)
    dropped_seeds: list[dict] = field(default_factory=list)
    repeat_seeds: list[dict] = field(default_factory=list)


def init_run(store: Store, brief: dict) -> Run:
    brief_id = brief["brief_id"]
    run_dir = store.root / "runs" / brief_id
    if run_dir.exists():
        raise Blocked(f"run dir exists: {brief_id}")
    run_dir.mkdir(parents=True)
    nonce = secrets.token_bytes(32)
    (run_dir / "run_nonce").write_bytes(nonce)
    atomic_write_yaml(run_dir / "brief.yaml", brief)
    return Run(id=brief_id, dir=run_dir, brief=brief, nonce=nonce)


def materialize_hints(run: Run, alloc: dict, brief: dict, packs: dict[str, Path] | None = None) -> None:
    packs = packs or {}
    for lid, sl in alloc.items():
        jail = ensure_jail(run.dir, lid)
        hints_dir = jail / "hints"
        for p in hints_dir.glob("*"):
            if p.is_file():
                p.unlink()
        kind = sl["evidence_kind"]
        src = packs.get(kind)
        if src and src.is_file():
            (hints_dir / src.name).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            body = []
            for h in sl.get("hint_strings") or []:
                body.append(f"{h} source: {h}")
            (hints_dir / f"{kind}.txt").write_text("\n".join(body) + "\n", encoding="utf-8")


def mint_anon(nonce: bytes, local_id: str) -> str:
    return "A-" + hmac.new(nonce, local_id.encode(), hashlib.sha256).hexdigest()[:12]


def prior_sets_for(store: Store, domain: str, n: int = PRIOR_N) -> list[set[str]]:
    qs = [q for q in store.load_status("SCORED", "ADOPTED")
          if (q.get("lineage") or {}).get("domain") == domain]
    return [token_set(q) for q in qs[-n:]]


def diversity_ok(seeds: list, prior_sets: list[set[str]],
                 th_mean: float = TH_MEAN, th_pair: float = TH_PAIR) -> bool:
    if len(seeds) < 2:
        return False
    sets = [token_set(s) for s in seeds]
    pairs = [jaccard(sets[i], sets[j]) for i in range(len(sets)) for j in range(i + 1, len(sets))]
    if max(pairs) > th_pair:
        return False
    prior = [jaccard(token_set(s), p) for s in seeds for p in prior_sets]
    pool = pairs + prior
    return (sum(pool) / len(pool)) <= th_mean


def flatten_seeds(accepted: dict[str, list], run_id: str,
                  dropped: list[dict] | None = None) -> list:
    """Ingest is a trust boundary; validate here, not only on the worker side.

    The worker runs `if_lwar.py --validate-only`, but nothing re-checked its
    outbox, so a malformed seed reached compose and judge unvalidated.
    RUN-20260820-live7 died on `TypeError` in judge because one `unknowns`
    entry was a dict: the worker wrote an unquoted YAML scalar containing
    ": ", which YAML parses as a mapping. The content was right and the
    serialisation was not, and the whole nine-question run was lost to it.

    A bad seed is dropped, not fatal, and recorded so the loss is visible.
    """
    out = []
    for lid, box in accepted.items():
        for s in box or []:
            try:
                validate_obj("seed_outbox", s)
            except SchemaError as error:
                if dropped is not None:
                    dropped.append({
                        "lwar_id": lid,
                        "local_id": s.get("local_id") if isinstance(s, dict) else None,
                        "reason": str(error),
                    })
                continue
            try:
                out.append(stamp_lineage(s, lid, run_id))
            except Drop:
                continue
    return out


def explore_loop(store: Store, run: Run, alloc: dict, lwars: list, packs=None) -> list:
    prior = prior_sets_for(store, run.brief["domain"])
    seeds, rounds = [], 0
    max_rounds = run.brief.get("budget", {}).get("max_rounds", 3)
    while rounds < max_rounds:
        accepted = {}
        for lid, sl in alloc.items():
            jail = ensure_jail(run.dir, lid)
            inbox = {
                "role": "generate",
                "run_id": run.id,
                "domain": run.brief["domain"],
                "lwar_id": lid,
                "allocation_slice": sl,
            }
            got = generate(inbox, hint_dir=jail / "hints")
            accepted[lid] = got
            run.observed_statuses.append("succeeded")
        seeds = flatten_seeds(accepted, run.id, run.dropped_seeds)
        if diversity_ok(seeds, prior):
            return seeds
        if rounds == max_rounds - 1:
            if len(seeds) < 2:
                return seeds
            raise Blocked("diversity_failed")
        alloc = inject_divergence(alloc, run.brief)
        atomic_write_yaml(run.dir / "allocation.yaml", alloc)
        materialize_hints(run, alloc, run.brief, packs)
        rounds += 1
    return seeds


def cross_assign(seeds: list, lwars: list, forbid_ids: dict[str, set]) -> dict:
    assign, i = {}, 0
    ids = [w["lwar_id"] for w in lwars]
    for s in seeds:
        banned = forbid_ids.get(s["local_id"], set())
        tried = 0
        while ids[i % len(ids)] in banned:
            i += 1
            tried += 1
            if tried > len(ids):
                raise Blocked(f"no examiner for {s['local_id']}")
        assign.setdefault(ids[i % len(ids)], []).append(s)
        i += 1
    return assign


def exploit_loop(run: Run, seeds: list, lwars: list, mode: str) -> tuple[dict, dict]:
    if mode == "normal" and len(lwars) < 3:
        raise Blocked("normal mode needs 3 LWARs")
    c_forb = {s["local_id"]: {s["lineage"]["generated_by"]} for s in seeds}
    c_asg = cross_assign(seeds, lwars, c_forb)
    dissents = {}
    for lid, qs in c_asg.items():
        recs = cross_examine({
            "lwar_id": lid,
            "forbidden_premises": run.brief.get("forbidden_premises") or [],
            "questions": qs,
        })
        for r in recs:
            dissents[r["local_id"]] = r
        run.observed_statuses.append("succeeded")
    j_forb = {s["local_id"]: {s["lineage"]["generated_by"]} for s in seeds}
    if mode == "normal":
        for s in seeds:
            d = dissents.get(s["local_id"])
            if d:
                j_forb[s["local_id"]].add(d["examiner"])
    j_asg = cross_assign(seeds, lwars, j_forb)
    anon_map, cards_raw = {}, []
    for lid, qs in j_asg.items():
        blinded, excl = [], set()
        for q in qs:
            aid = mint_anon(run.nonce, q["local_id"])
            anon_map[aid] = q["local_id"]
            blinded.append(blind_packet(q, aid))
            excl |= j_forb[q["local_id"]]
        recs = judge({
            "lwar_id": lid,
            "exclude_lwars": list(excl),
            "questions": blinded,
        })
        cards_raw.extend(recs)
        run.observed_statuses.append("succeeded")
    cards = {}
    seen = set()
    for card in cards_raw:
        aid = card.get("anon_id")
        if not aid or aid not in anon_map or aid in seen:
            continue
        seen.add(aid)
        cards[anon_map[aid]] = {**card, "local_id": anon_map[aid]}
    if mode == "normal":
        missing = [s["local_id"] for s in seeds if s["local_id"] not in dissents]
        if missing:
            raise Blocked("protocol_incomplete")
    return dissents, cards


def compute_protocol_valid(obs: dict) -> bool:
    return all([
        obs["mode"] == "normal",
        obs["n_lwars"] >= 3,
        obs["contributing_generate_lwars"] >= 3,
        obs["protocol_error_count"] == 0,
        obs["seed_count"] > 0 and obs["qo_count"] == obs["seed_count"],
        obs["all_unknown_ref"],
        obs["dissent_coverage"],
        obs["vendor_families"] >= 2,
    ])


def fail_report(run: Run, reason: str) -> dict:
    return {
        "run_id": run.id,
        "mode": run.brief.get("mode", "normal"),
        "separation": "ablation" if run.brief.get("mode") == "ablation" else "full",
        "protocol_valid": False,
        "hypothesis_valid": False,
        "seed_count": 0,
        "qo_count": 0,
        "scored_count": 0,
        "human": "failed",
        "dissent_referenced": False,
        "slo_scored_ge_8": False,
        "dropped_seeds": run.dropped_seeds,
        "repeat_seeds": run.repeat_seeds,
        "contributing_generate_lwars": 0,
        "observed_statuses": run.observed_statuses,
        "reason": reason,
    }


def explore_loop_pao(store: Store, run: Run, alloc: dict, lwars: list, packs=None) -> list:
    items = []
    for lid, sl in alloc.items():
        inbox = {
            "schema": "if.task.v1",
            "role": "generate",
            "run_id": run.id,
            "domain": run.brief["domain"],
            "lwar_id": lid,
            "phase": "EXPLORE",
            "allocation_slice": sl,
            "stub": bool(run.brief.get("stub")),
        }
        items.append((lid, inbox))
    timeout = int(run.brief.get("budget", {}).get("generate_timeout_s") or 900)
    accepted, statuses = publish_collect(run.dir, "generate", items, timeout)
    run.observed_statuses.extend(statuses)
    seeds = flatten_seeds(accepted, run.id, run.dropped_seeds)
    note_repeats(store, run, seeds)
    return seeds


def note_repeats(store: Store, run: Run, seeds: list) -> None:
    """Record seeds that repeat an earlier question in this domain.

    `diversity_ok` has always existed and is called only from `explore_loop`,
    the local path. Every live run has used `--pao`, so nothing ever compared a
    seed against earlier work: RUN-20260821-live8 repeated three of
    RUN-20260820-live7b's questions at a token-set Jaccard of 1.00 and the
    pipeline reported a clean run.

    Recorded rather than dropped. A repeat is not malformed, dropping it would
    shrink the run below its own protocol checks, and the operator reviewing
    the run is the one who should decide what a repeat is worth. Prior sets
    come from SCORED and ADOPTED only, so a question parked in DORMANT for want
    of a judge does not suppress asking it again — it never got its answer.
    """
    prior = prior_sets_for(store, run.brief["domain"])
    if not prior:
        return
    for s in seeds:
        ts = token_set(s)
        best = max((jaccard(ts, p) for p in prior), default=0.0)
        if best > TH_PAIR:
            run.repeat_seeds.append({
                "local_id": s["local_id"],
                "lwar_id": s["lineage"]["generated_by"],
                "operator": s.get("operator"),
                "max_prior_jaccard": round(best, 3),
            })


def exploit_loop_pao(run: Run, seeds: list, lwars: list, mode: str) -> tuple[dict, dict]:
    if mode == "normal" and len(lwars) < 3:
        raise Blocked("normal mode needs 3 LWARs")
    stub = bool(run.brief.get("stub"))
    c_forb = {s["local_id"]: {s["lineage"]["generated_by"]} for s in seeds}
    c_asg = cross_assign(seeds, lwars, c_forb)
    c_items = []
    for lid, qs in c_asg.items():
        c_items.append((lid, {
            "schema": "if.task.v1",
            "role": "contrarian",
            "run_id": run.id,
            "lwar_id": lid,
            "phase": "EXPLOIT",
            "forbidden_premises": run.brief.get("forbidden_premises") or [],
            "questions": qs,
            "stub": stub,
        }))
    timeout = int(run.brief.get("budget", {}).get("contrarian_timeout_s") or 900)
    accepted, statuses = publish_collect(run.dir, "contrarian", c_items, timeout)
    run.observed_statuses.extend(statuses)
    dissents = {}
    for recs in accepted.values():
        for r in recs or []:
            if r.get("local_id"):
                dissents[r["local_id"]] = r
    j_forb = {s["local_id"]: {s["lineage"]["generated_by"]} for s in seeds}
    if mode == "normal":
        for s in seeds:
            d = dissents.get(s["local_id"])
            if d and d.get("examiner"):
                j_forb[s["local_id"]].add(d["examiner"])
    j_asg = cross_assign(seeds, lwars, j_forb)
    j_items = []
    anon_map = {}
    for lid, qs in j_asg.items():
        blinded, excl = [], set()
        for q in qs:
            aid = mint_anon(run.nonce, q["local_id"])
            anon_map[aid] = q["local_id"]
            blinded.append(blind_packet(q, aid))
            excl |= j_forb[q["local_id"]]
        j_items.append((lid, {
            "schema": "if.task.v1",
            "role": "judge",
            "run_id": run.id,
            "lwar_id": lid,
            "phase": "EXPLOIT",
            "exclude_lwars": sorted(excl),
            "questions": blinded,
            "stub": stub,
        }))
    j_timeout = int(run.brief.get("budget", {}).get("judge_timeout_s") or 600)
    j_acc, j_st = publish_collect(run.dir, "judge", j_items, j_timeout)
    run.observed_statuses.extend(j_st)
    cards_raw = []
    for recs in j_acc.values():
        cards_raw.extend(recs or [])
    cards, seen = {}, set()
    for card in cards_raw:
        aid = card.get("anon_id")
        if not aid or aid not in anon_map or aid in seen:
            continue
        seen.add(aid)
        cards[anon_map[aid]] = {**card, "local_id": anon_map[aid]}
    if mode == "normal":
        missing = [s["local_id"] for s in seeds if s["local_id"] not in dissents]
        if missing:
            raise Blocked("protocol_incomplete")
    return dissents, cards


def reject_excluded(lwars: list[dict]) -> None:
    """Refuse a roster containing an excluded vendor family or adapter.

    Rejects the roster rather than silently filtering it: dropping members
    would quietly turn a three-LWAR run into a two-LWAR one and change what the
    heterogeneity checks are measuring, which is exactly the kind of invisible
    reshaping that makes a run hard to reason about afterwards. The operator
    passes the roster, so the operator fixes it.
    """
    bad = []
    for lwar in lwars:
        fam = vendor_family(lwar)
        if fam in EXCLUDE_FAMILIES:
            bad.append(f"{lwar.get('lwar_id')} (vendor_family={fam})")
            continue
        adapter = lwar.get("adapter_id") or (lwar.get("profile") or {}).get("adapter_id")
        if adapter and str(adapter).lower() in EXCLUDE_ADAPTERS:
            bad.append(f"{lwar.get('lwar_id')} (adapter_id={adapter})")
    if bad:
        raise Blocked("excluded from IF runs: " + ", ".join(bad))


def inquiry_cycle(brief: dict, lwars: list[dict], if_root=None, packs=None, pao: bool = False) -> dict:
    if not (brief.get("evidence_hints") or {}):
        raise Blocked("evidence_hints empty")
    reject_excluded(lwars)
    mode = brief.get("mode", "normal")
    if mode == "normal" and len(lwars) < 3:
        raise Blocked("normal mode needs >= 3 LWARs")
    if len(lwars) < 2:
        raise Blocked("need >= 2 LWARs")
    store = Store(if_root)
    run = init_run(store, brief)
    alloc = build_allocation(brief, lwars, store.query_avoid_patterns(brief["domain"]))
    atomic_write_yaml(run.dir / "allocation.yaml", alloc)
    materialize_hints(run, alloc, brief, packs)
    if pao:
        seeds = explore_loop_pao(store, run, alloc, lwars, packs)
    else:
        seeds = explore_loop(store, run, alloc, lwars, packs)
    if not seeds:
        rep = fail_report(run, "empty_unknowns_or_seeds")
        atomic_write_yaml(run.dir / "report.yaml", rep)
        return rep
    if pao:
        dissents, cards = exploit_loop_pao(run, seeds, lwars, mode)
    else:
        dissents, cards = exploit_loop(run, seeds, lwars, mode)
    qos = compose(store, run.dir, run.id, seeds, dissents, cards,
                  brief.get("evidence_hints") or {}, mode)
    human = open_review(store, run.dir, run.id, qos)
    scored = [q for q in qos if q["status"] == "SCORED"]
    contrib = {s["lineage"]["generated_by"] for s in seeds}
    valid = compute_protocol_valid({
        "mode": mode,
        "n_lwars": len(lwars),
        "contributing_generate_lwars": len(contrib),
        "protocol_error_count": run.observed_statuses.count("protocol_error"),
        "seed_count": len(seeds),
        "qo_count": len(qos),
        "all_unknown_ref": all(s.get("unknown_ref") for s in seeds),
        "dissent_coverage": mode != "normal" or len(dissents) == len(seeds),
        "vendor_families": len({vendor_family(w) for w in lwars}),
    })
    report = {
        "run_id": run.id,
        "mode": mode,
        "separation": "full" if mode == "normal" else "ablation",
        "protocol_valid": valid,
        "hypothesis_valid": valid,
        "seed_count": len(seeds),
        "qo_count": len(qos),
        "scored_count": len(scored),
        "human": human["status"],
        "dissent_referenced": human.get("dissent_referenced", True),
        "slo_scored_ge_8": len(scored) >= 8,
        "contributing_generate_lwars": len(contrib),
        "observed_statuses": run.observed_statuses,
        # Seeds a worker produced and ingest refused. Not fatal, but never
        # silent: a run that quietly shrank looks the same as one that was
        # small to begin with.
        "dropped_seeds": run.dropped_seeds,
        # Seeds no judge ever scored. protocol_valid stays true for these —
        # the protocol was followed and a runtime died — so without this the
        # headline field reads clean on a run that lost a third of its
        # judging, as RUN-20260820-live7b did.
        "unjudged": [s["local_id"] for s in seeds if s["local_id"] not in cards],
        # Seeds that repeat an earlier SCORED/ADOPTED question in this domain.
        "repeat_seeds": run.repeat_seeds,
    }
    atomic_write_yaml(run.dir / "report.yaml", report)
    return report


def close_run(if_root, run_id: str) -> dict:
    store = Store(if_root)
    return close_review(store, store.root / "runs" / run_id)
