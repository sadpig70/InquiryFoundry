"""Walk ifa batches over the adopted-question portfolio, unattended.

Promoted from session scratch after two full portfolio walks and three
qualification passes ran through it -- a driver that only exists in a
session's temp directory is one session-end away from being a rumor in
HANDOFF. Everything session-specific is gone: the repo root comes from this
file's location and the OA identity must arrive via PAO_OA_ID.

    set PAO_OA_ID=oa-...           (required; mint per OA session)
    python tools/ifa_walk.py rounds            # select+predict/rebut/adjudicate
    python tools/ifa_walk.py reviews           # review/ratify/close + scoreboard
    IFA_SELECT_MODE=fresh|second-opinion|contested   (default second-opinion)

rounds needs >=2 candidate-family sessions parked on the doorbell; reviews
needs the anthropic reviewer parked. The phases are decoupled on purpose:
rounds bank work while the reviewer sleeps, and neither half waits on the
other. Candidates and the reviewer are found by vendor family at batch time,
never by slot number -- slots recycle across generations.
"""
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IFA = ROOT / ".agents" / "skills" / "ifa-core" / "scripts" / "ifa.py"
CANDIDATE_FAMILIES = {"zai", "alibaba", "moonshot", "deepseek", "xai", "openai", "google"}
REVIEWER_FAMILY = "anthropic"
BATCH = 8
SELECT_MODE = os.environ.get("IFA_SELECT_MODE", "second-opinion")

if not os.environ.get("PAO_OA_ID"):
    sys.exit("PAO_OA_ID is required (mint one per OA session)")
ENV = os.environ.copy()


def sh(args, timeout=None):
    p = subprocess.run([sys.executable, str(IFA), *args], cwd=ROOT, env=ENV,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=timeout)
    out = (p.stdout or "").strip()
    try:
        return json.loads(out[out.index("{"):]) if "{" in out else {}
    except (ValueError, json.JSONDecodeError):
        return {"raw": out[-300:], "rc": p.returncode}


def watching():
    try:
        d = json.loads((ROOT / ".pao" / "var" / "pao_server.json").read_text(encoding="utf-8"))
        return set(d.get("watching") or [])
    except (OSError, json.JSONDecodeError):
        return set()


def slots_by_family():
    try:
        reg = json.loads((ROOT / ".pao" / "var" / "registry" / "lwar_registry.json")
                         .read_text(encoding="utf-8"))
        return {k: (v.get("profile") or {}).get("vendor_family")
                for k, v in reg.get("slots", {}).items()}
    except (OSError, json.JSONDecodeError):
        return {}


def candidates_now():
    fams = slots_by_family()
    pool = {k for k, f in fams.items() if f in CANDIDATE_FAMILIES}
    return sorted(pool & watching())


def reviewer_now():
    for k, f in sorted(slots_by_family().items()):
        if f == REVIEWER_FAMILY:
            return k
    return None


def next_batch_no():
    nums = [int(m.group(1)) for d in (ROOT / ".ifa" / "runs").glob("RUN-IFA-*-q*")
            if (m := re.search(r"-q(\d+)$", d.name))]
    return max(nums, default=0) + 1


def rounds():
    stamp = time.strftime("%Y%m%d")
    done = 0
    start = next_batch_no()
    for i in range(start, start + 12):
        run_id = f"RUN-IFA-{stamp}-q{i:02d}"
        sel = sh(["select", "--run", run_id, "--n", str(BATCH), "--mode", SELECT_MODE])
        qids = sel.get("selected") or []
        if not qids:
            print("POOL EXHAUSTED after %d batches (mode=%s)" % (done, SELECT_MODE), flush=True)
            break
        t0 = time.time()
        active = candidates_now()
        while len(active) < 2 and time.time() - t0 < 1800:
            time.sleep(20)
            active = candidates_now()
        if len(active) < 2:
            print(f"STALL {run_id}: candidates parked={active}", flush=True)
            break
        print(f"[{run_id}] {len(qids)} questions -> {active}", flush=True)
        rep = sh(["run", "--run", run_id, "--lwars", ",".join(active)], timeout=3600)
        if rep.get("status") != "predicted":
            print(f"[{run_id}] ROUND FAILED: {json.dumps(rep, ensure_ascii=False)[:300]}", flush=True)
            break
        print(f"[{run_id}] answers={len(rep.get('answers') or [])} "
              f"dropped={[d['lwar_id'] for d in rep.get('dropped') or []]}", flush=True)
        done += 1
    print(f"ROUNDS DONE batches={done}", flush=True)


def reviews():
    import yaml
    for rd in sorted((ROOT / ".ifa" / "runs").glob("RUN-IFA-*-q*")):
        rep_p = rd / "report.yaml"
        if not rep_p.is_file():
            continue
        rep = yaml.safe_load(rep_p.read_text(encoding="utf-8")) or {}
        if rep.get("human") != "awaiting_review":
            continue
        run_id = rd.name
        rv_slot = reviewer_now()
        t0 = time.time()
        while (not rv_slot or rv_slot not in watching()) and time.time() - t0 < 1800:
            time.sleep(20)
            rv_slot = reviewer_now()
        if not rv_slot or rv_slot not in watching():
            print("REVIEWER UNAVAILABLE (anthropic slot: %s)" % rv_slot, flush=True)
            break
        rv = sh(["review-run", "--run", run_id, "--lwar-id", rv_slot,
                 "--by", "Claude Fable 5"], timeout=1500)
        if rv.get("status") != "recommended":
            print(f"[{run_id}] REVIEW FAILED: {json.dumps(rv, ensure_ascii=False)[:200]}", flush=True)
            break
        # Calibration anchors: previously-decided cases re-judged blind.
        review_doc = yaml.safe_load((rd / "review.yaml").read_text(encoding="utf-8")) or {}
        ar = review_doc.get("anchor_report")
        if ar:
            print(f"[{run_id}] anchor drift: {ar.get('flipped')}/{ar.get('judged')}"
                  f" = {ar.get('drift')}", flush=True)
        sh(["ratify", "--run", run_id, "--reviewer", "Claude Fable 5", "--delegated"])
        cl = sh(["close", "--run", run_id])
        print(f"[{run_id}] closed {json.dumps(cl.get('decided'), ensure_ascii=False)}", flush=True)
    print("SCOREBOARD (instance-keyed):", flush=True)
    vs = sh(["vendors", "--run", "x"])
    for k in sorted(vs):
        v = vs[k]
        print("  %-24s reg=%s disc=%s rate=%s" % (k, v.get("registered"),
              v.get("discarded"), v.get("rate")), flush=True)


if __name__ == "__main__":
    {"rounds": rounds, "reviews": reviews}[sys.argv[1]]()
