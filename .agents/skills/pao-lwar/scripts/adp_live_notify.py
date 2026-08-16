#!/usr/bin/env python3
"""live-notify watcher: stay up and emit each event on stdout while running."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pao_runtime.adp_watch import run_live_notify  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="adp-live-notify",
        description="live-notify ADP watcher: keep polling; print one JSON line per event",
    )
    parser.add_argument("--identity-file")
    parser.add_argument("--root", default=None)
    parser.add_argument("--interval", type=float, default=5.0)
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument("--lease-seconds", type=int, default=180)
    args = parser.parse_args()
    identity = args.identity_file or os.environ.get("PAO_LWAR_IDENTITY")
    if not identity:
        raise SystemExit("adp-live-notify requires --identity-file or PAO_LWAR_IDENTITY")
    return run_live_notify(
        identity,
        root=args.root,
        interval=args.interval,
        timeout=args.timeout,
        lease_seconds=args.lease_seconds,
    )


if __name__ == "__main__":
    raise SystemExit(main())
