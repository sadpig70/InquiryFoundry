"""Poll OA collect until the three live1 contrarian tasks complete."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time

OA = r"D:\InquiryFoundry\.agents\skills\pao-oa\scripts\oa.py"
os.environ["PAO_OA_ID"] = os.environ.get("PAO_OA_ID", "oa-d2cf906650c14ee19364868369bcf574")
WANT = {
    "task-if-RUN-20260814-live1-contrarian-LWAR1-r0",
    "task-if-RUN-20260814-live1-contrarian-LWAR2-r0",
    "task-if-RUN-20260814-live1-contrarian-LWAR3-r1",
}


def main() -> int:
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        subprocess.run(
            [sys.executable, OA, "collect"],
            cwd=r"D:\InquiryFoundry",
            capture_output=True,
            text=True,
        )
        p = subprocess.run(
            [sys.executable, OA, "workflow-status", "--workflow-id", "workflow-if-run-20260814-live1"],
            cwd=r"D:\InquiryFoundry",
            capture_output=True,
            text=True,
        )
        data = json.loads(p.stdout or "{}")
        bits = []
        done = 0
        for t in data.get("tasks") or []:
            if t["task_id"] in WANT:
                bits.append(f"{t['lwar_id']}:{t['status']}:{t.get('result_status')}")
                if t["status"] == "completed":
                    done += 1
        print("WF " + " ".join(bits), flush=True)
        if done == 3:
            print("ALL_CONTRARIAN_COMPLETED", flush=True)
            return 0
        time.sleep(15)
    print("WAIT_TIMEOUT", flush=True)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
