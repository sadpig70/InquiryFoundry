#!/usr/bin/env python3
"""exit-notify watcher: exit on first task/control or after 50 idle minutes."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pao_runtime.adp_watch import EXIT_NOTIFY_MAX_RUNTIME_S, run_exit_notify  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="adp-exit-notify",
        description="exit-notify ADP watcher: emit JSON then exit so the host can read stdout",
    )
    parser.add_argument("--identity-file")
    parser.add_argument("--root", default=None)
    parser.add_argument("--interval", type=float, default=5.0)
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument("--lease-seconds", type=int, default=180)
    parser.add_argument(
        "--max-runtime-s",
        type=float,
        default=EXIT_NOTIFY_MAX_RUNTIME_S,
        help="idle cap in seconds (default 3000 = 50m)",
    )
    args = parser.parse_args()
    identity = args.identity_file or os.environ.get("PAO_LWAR_IDENTITY")
    if not identity:
        raise SystemExit("adp-exit-notify requires --identity-file or PAO_LWAR_IDENTITY")
    return run_exit_notify(
        identity,
        root=args.root,
        interval=args.interval,
        timeout=args.timeout,
        lease_seconds=args.lease_seconds,
        max_runtime_s=args.max_runtime_s,
    )


if __name__ == "__main__":
    raise SystemExit(main())
