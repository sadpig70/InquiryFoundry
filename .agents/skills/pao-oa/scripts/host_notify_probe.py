#!/usr/bin/env python
"""One-shot stdout probe for live-notify vs exit-notify.

Prints PAO_LIVE, sleeps, prints PAO_EXIT. Each marker carries the wall-clock
time and the elapsed seconds at which the process *emitted* it, so the evidence
survives outside the session's memory.

The distinction the probe exists for is about **delivery**, and only the calling
session can judge that: did PAO_LIVE reach you before the process exited, with
no polling on your part? The timestamps do not answer that. What they do is
separate a host that batched both lines at exit (markers emitted seconds apart,
delivered together) from a probe that misbehaved (markers emitted together) —
without which "both lines arrived at once" is ambiguous.
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

SLEEP_S = 5.0


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--record",
        default=None,
        help=(
            "optional path to write the emitted markers as JSON. Records only "
            "what this process did; the notify_style judgment stays with the "
            "session. Choose a path outside the bus mailbox."
        ),
    )
    args = parser.parse_args()

    started = time.monotonic()
    markers = []

    # Marker token stays first on the line so existing greps keep working.
    live_at = _now()
    print(f"PAO_LIVE emitted_at={live_at} elapsed_s=0.000", flush=True)
    markers.append({"marker": "PAO_LIVE", "emitted_at": live_at, "elapsed_s": 0.0})

    time.sleep(SLEEP_S)

    exit_elapsed = round(time.monotonic() - started, 3)
    exit_at = _now()
    print(f"PAO_EXIT emitted_at={exit_at} elapsed_s={exit_elapsed:.3f}", flush=True)
    markers.append({"marker": "PAO_EXIT", "emitted_at": exit_at, "elapsed_s": exit_elapsed})

    if args.record:
        path = Path(args.record)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "probe": "host_notify_probe",
                    "sleep_s": SLEEP_S,
                    "markers": markers,
                    "note": (
                        "Emission times only. notify_style and blocking_required "
                        "are judged by the session from how these lines were "
                        "delivered, not from this file."
                    ),
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
