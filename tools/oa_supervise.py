"""OA presence cadence while waiting for LWAR registrations. PYTHONUNBUFFERED=1."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / ".agents" / "skills" / "if-core"))
from if_core.const import EXCLUDE_ADAPTERS, EXCLUDE_FAMILIES  # noqa: E402

OA_ID = os.environ.get("PAO_OA_ID", "oa-d2cf906650c14ee19364868369bcf574")
OA = str(_REPO / ".agents" / "skills" / "pao-oa" / "scripts" / "oa.py")
os.environ["PAO_OA_ID"] = OA_ID
os.chdir(str(_REPO))

last = None
ready_announced = False
lock_backoff = 0.0


def run(args: list[str]) -> tuple[int, str]:
    p = subprocess.run([sys.executable, OA, *args], capture_output=True, text=True)
    return p.returncode, (p.stdout or "").strip()


while True:
    t0 = time.monotonic()
    if lock_backoff > time.monotonic():
        time.sleep(min(5.0, lock_backoff - time.monotonic()))
        continue
    rc_p, out_p = run(["presence"])
    if rc_p != 0:
        print(f"OA presence_fail rc={rc_p}", flush=True)
        if "lock" in (out_p or "").lower() or "lease" in (out_p or "").lower():
            lock_backoff = time.monotonic() + 20.0
            continue
    rc_r, rec = run(["reconcile"])
    if rc_r == 0:
        try:
            ev = json.loads(rec)
            if ev.get("registrations") or ev.get("lifecycles"):
                print(
                    f"OA reconcile registrations={ev.get('registrations')} "
                    f"lifecycles={ev.get('lifecycles')} quarantined={ev.get('quarantined')}",
                    flush=True,
                )
        except json.JSONDecodeError:
            print(f"OA reconcile {rec[:200]}", flush=True)
    rc_s, st = run(["status"])
    if rc_s == 0:
        try:
            data = json.loads(st)
            lwars = data.get("lwars") or []
            bits = []
            active = 0
            families = set()
            for L in lwars:
                prof = L.get("profile") or {}
                fam = L.get("vendor_family") or prof.get("vendor_family") or "?"
                adp = prof.get("adapter_id") or ""
                rs = L.get("runtime_status") or "?"
                excluded = fam in EXCLUDE_FAMILIES or adp in EXCLUDE_ADAPTERS
                bits.append(f"{L.get('lwar_id')}:{L.get('state')}:{rs}:{fam}{'-EXCL' if excluded else ''}")
                if excluded and L.get("state") == "on":
                    run(["control", "--lwar-id", L["lwar_id"], "--command", "drain"])
                    print(f"OA EXCLUDE drain {L.get('lwar_id')} family={fam} adapter={adp}", flush=True)
                    continue
                if L.get("state") == "on" and rs == "active":
                    active += 1
                    if fam and fam != "?":
                        families.add(fam)
            line = f"OA n={len(lwars)} active={active} families={len(families)} [{','.join(bits)}]"
            if line != last:
                print(line, flush=True)
                last = line
            if (not ready_announced) and active >= 3 and len(families) >= 2:
                print("OA READY live_heterogeneous_lwar>=3", flush=True)
                ready_announced = True
        except json.JSONDecodeError:
            print(f"OA status_raw {st[:240]}", flush=True)
    elapsed = time.monotonic() - t0
    time.sleep(max(1.0, min(25.0 - elapsed, 25.0)))
