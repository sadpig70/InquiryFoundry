#!/usr/bin/env python3
"""Secondary Kimi fallback: recycle a detached --background watcher every 55 minutes.

Do not use this when --detach stays alive (the normal path). Identity MUST come
from --identity-file or PAO_LWAR_IDENTITY. No hardcoded paths.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

WATCHER = Path(__file__).with_name("adp_watch.py")
LWAR = Path(__file__).with_name("lwar.py")
DEFAULT_RECYCLE_S = 55 * 60


def resolve_identity(value: str | None) -> Path:
    raw = value or os.environ.get("PAO_LWAR_IDENTITY")
    if not raw:
        raise SystemExit("pass --identity-file or set PAO_LWAR_IDENTITY")
    path = Path(raw).resolve()
    if not path.is_file():
        raise SystemExit(f"identity file not found: {path}")
    return path


def main() -> int:
    p = argparse.ArgumentParser(description="Recycle detached ADP watcher (Kimi 1h fallback)")
    p.add_argument("--identity-file")
    p.add_argument("--recycle-s", type=int, default=DEFAULT_RECYCLE_S)
    p.add_argument("--report-every", type=float, default=86400.0)
    p.add_argument("--detach-self", action="store_true", help="spawn this recycler detached and exit")
    args = p.parse_args()
    if args.recycle_s <= 0:
        raise SystemExit("--recycle-s must be positive")
    identity = resolve_identity(args.identity_file)
    if args.detach_self:
        from pao_runtime.detach import child_argv_without_detach, spawn_detached

        argv = [sys.executable, *child_argv_without_detach()]
        # child_argv still contains --detach-self; strip it
        argv = [a for a in argv if a != "--detach-self"]
        pid = spawn_detached(argv)
        print(f'{{"event":"recycle_detached","pid":{pid}}}', flush=True)
        return 0
    while True:
        start = subprocess.run(
            [
                sys.executable,
                "-u",
                str(WATCHER),
                "--identity-file",
                str(identity),
                "--background",
                "--detach",
                "--report-every",
                str(args.report_every),
            ],
            check=False,
        )
        if start.returncode != 0:
            return start.returncode
        time.sleep(args.recycle_s)
        subprocess.run(
            [sys.executable, str(WATCHER), "--identity-file", str(identity), "--stop"],
            check=False,
        )


if __name__ == "__main__":
    raise SystemExit(main())
