"""Does the avoid loop actually stop defects from coming back?

Everything the feedback loop was built for rests on that one claim, and it had
never been measured. This reports what can be measured without judgment:

  recurrence  a rejected question reappearing in a later run of the same domain,
              scored by character similarity. Verbatim (1.00) is the hard case;
              anything lower is a judgment call and is printed, not counted.
  blindness   a run allocated before the previous run of that domain closed. Its
              generators were briefed with feedback that did not exist yet, so a
              recurrence there is a scheduling artifact and not a loop failure.
  reject rate the coarse outcome. Recurrence can fall while this stays flat --
              they are different claims and are kept apart on purpose.

Codes are reported separately: the taxonomy only reached generators at live13,
so per-code recurrence intervals are not yet computable and this says so rather
than printing a number built on two rejects.

    python tools/if_recurrence.py [--if-root .if] [--threshold 0.55]
"""
from __future__ import annotations

import argparse
import datetime as dt
import difflib
import json
import sys
from pathlib import Path

import yaml

VERBATIM = 0.995


def load_questions(store):
    out = []
    for status in ("ADOPTED", "REJECTED", "DEFERRED", "REVIEWED",
                   "SCORED", "DORMANT", "MERGED", "QUARANTINE"):
        for q in store.load_status(status):
            lin = q.get("lineage") or {}
            if not lin.get("run_id"):
                continue
            out.append({"qid": q["question_id"], "status": status,
                        "run": lin["run_id"], "domain": lin.get("domain"),
                        "text": q.get("question") or ""})
    return out


def similarity(a, b):
    return difflib.SequenceMatcher(None, "".join(a.split()), "".join(b.split())).ratio()


def close_times(if_root):
    """First decision timestamp of a run is when its review closed."""
    closed = {}
    f = if_root / "memory" / "decisions.jsonl"
    for line in f.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        closed.setdefault(r["run_id"], dt.datetime.fromisoformat(r["ts"]))
    return closed


def allocated_at(if_root, run):
    f = if_root / "runs" / run / "allocation.yaml"
    return dt.datetime.fromtimestamp(f.stat().st_mtime, dt.UTC) if f.is_file() else None


def delivered(if_root, run):
    """(codes, window, withheld) actually handed to generators.

    The two blocks swapped fields at live13: `avoid_registry` carries the
    persistent taxonomy, `avoid_patterns` the verbatim recent window. Reading
    only the field named "avoid_patterns" mislabels every run on either side.

    `withheld` separates a control arm from a run that simply had no codes to
    send -- both show zero. Runs predating the flag report None, which is not
    False: it means the record cannot say, and those runs are all pre-taxonomy.
    """
    f = if_root / "runs" / run / "allocation.yaml"
    if not f.is_file():
        return 0, 0, None
    slots = list((yaml.safe_load(f.read_text(encoding="utf-8")) or {}).values())
    if not slots:
        return 0, 0, None
    flags = [s.get("avoid_codes_withheld") for s in slots]
    withheld = None if all(v is None for v in flags) else bool(any(flags))
    return (max(len(s.get("avoid_registry") or []) for s in slots),
            max(len(s.get("avoid_patterns") or []) for s in slots),
            withheld)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--if-root", default=".if")
    ap.add_argument("--threshold", type=float, default=0.55,
                    help="print near-duplicates at or above this similarity")
    args = ap.parse_args(argv)

    if_root = Path(args.if_root)
    sys.path.insert(0, str(Path(".agents/skills/if-core").resolve()))
    from if_core.store import Store

    store = Store(str(if_root))
    qs = load_questions(store)
    closed = close_times(if_root)
    decisions = [json.loads(l) for l in
                 (if_root / "memory" / "decisions.jsonl").read_text(encoding="utf-8").splitlines()
                 if l.strip()]

    runs = [r for r in sorted({q["run"] for q in qs}) if r in closed]
    order = {r: i for i, r in enumerate(runs)}

    # A run is blind when it was allocated before the run before it closed.
    blind, prev = {}, None
    for r in runs:
        a = allocated_at(if_root, r)
        blind[r] = bool(prev and a and a < closed[prev])
        prev = r

    print("%-22s %-11s %4s %4s %4s %5s  %5s %6s %-9s %-8s %s" % (
        "run", "domain", "n", "ado", "rej", "rej%", "codes", "window",
        "arm", "briefing", "recurrence"))
    totals = {"verbatim": 0, "near": 0, "blind_verbatim": 0}
    detail = []
    for run in runs:
        cur = [q for q in qs if q["run"] == run]
        dec = [d for d in decisions if d["run_id"] == run]
        ado = sum(1 for d in dec if d["decision"] == "adopt")
        rej = sum(1 for d in dec if d["decision"] == "reject")
        tot = len(dec)
        codes, window, withheld = delivered(if_root, run)
        prior = [q for q in qs if q["status"] == "REJECTED"
                 and order.get(q["run"], 1e9) < order[run]]
        best = []
        for q in cur:
            top = (0.0, None)
            for p in prior:
                if p["domain"] != q["domain"]:
                    continue
                s = similarity(q["text"], p["text"])
                if s > top[0]:
                    top = (s, p)
            best.append((top[0], q, top[1]))
        vb = [b for b in best if b[0] >= VERBATIM]
        nr = [b for b in best if args.threshold <= b[0] < VERBATIM]
        totals["verbatim"] += len(vb)
        totals["near"] += len(nr)
        if blind[run]:
            totals["blind_verbatim"] += len(vb)
        detail.extend(vb + nr)
        mark = "%d verbatim" % len(vb) if vb else ("%d near" % len(nr) if nr else "-")
        arm = "withheld" if withheld else ("-" if withheld is None else "given")
        print("%-22s %-11s %4d %4d %4d %4d%%  %5d %6d %-9s %-8s %s" % (
            run, cur[0]["domain"] if cur else "-", len(cur), ado, rej,
            round(100 * rej / tot) if tot else 0, codes, window, arm,
            "BLIND" if blind[run] else "informed", mark))

    print()
    if detail:
        print("recurrence detail (similarity, returning question, the reject it repeats)")
        for s, q, p in sorted(detail, key=lambda x: -x[0]):
            print("  %.2f  %s [%s] <- %s [%s]%s" % (
                s, q["qid"], q["run"], p["qid"], p["run"],
                "  (BLIND briefing)" if blind.get(q["run"]) else ""))
        print()

    informed_vb = totals["verbatim"] - totals["blind_verbatim"]
    print("verbatim recurrences: %d total, %d of them in blind runs, %d in informed runs"
          % (totals["verbatim"], totals["blind_verbatim"], informed_vb))
    print("near-duplicates at >=%.2f: %d" % (args.threshold, totals["near"]))

    coded = sum(1 for d in decisions if d.get("pattern") and " — " in d["pattern"])
    print("rejects carrying a taxonomy code: %d of %d -- per-code recurrence not yet computable"
          % (coded, sum(1 for d in decisions if d["decision"] == "reject")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
