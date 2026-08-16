#!/usr/bin/env python
"""Thin wrapper around pao-oa. Does not copy pao_runtime. No doctor. No graph writes."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ALLOWED = {
    "send", "collect", "recover", "status", "presence", "audit-health",
    "validate", "workflow-status", "control",
}


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in ALLOWED:
        print(
            "usage: if_oa.py <send|collect|recover|status|presence|audit-health|"
            "validate|workflow-status|control> ...",
            file=sys.stderr,
        )
        return 2
    oa = Path(__file__).resolve().parents[3] / "pao-oa" / "scripts" / "oa.py"
    return subprocess.call([sys.executable, str(oa), *sys.argv[1:]])


if __name__ == "__main__":
    raise SystemExit(main())
