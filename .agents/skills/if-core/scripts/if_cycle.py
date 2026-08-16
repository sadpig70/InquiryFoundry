#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from if_core.cycle import close_run, inquiry_cycle  # noqa: E402
from if_core.store import Blocked  # noqa: E402


def parse_lwars(s: str) -> list[dict]:
    out = []
    for part in s.split(","):
        lid, _, fam = part.partition(":")
        if not lid or not fam:
            raise SystemExit(f"lwar spec must be ID:family, got {part}")
        out.append({"lwar_id": lid.strip(), "vendor_family": fam.strip()})
    return out


def main() -> int:
    p = argparse.ArgumentParser(description="IF cycle runner")
    sub = p.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run")
    run.add_argument("--brief", required=True)
    run.add_argument("--if-root")
    run.add_argument("--lwars", required=True, help="LWAR1:anthropic,LWAR2:openai,LWAR3:alibaba")
    run.add_argument("--pack", action="append", default=[], help="kind=path")
    run.add_argument("--pao", action="store_true", help="publish via PAO bus (publish_collect)")
    close = sub.add_parser("close")
    close.add_argument("--run", required=True)
    close.add_argument("--if-root")
    args = p.parse_args()
    try:
        if args.cmd == "run":
            brief = yaml.safe_load(Path(args.brief).read_text(encoding="utf-8"))
            packs = {}
            for item in args.pack:
                k, _, v = item.partition("=")
                packs[k] = Path(v)
            report = inquiry_cycle(
                brief, parse_lwars(args.lwars), args.if_root, packs or None, pao=args.pao
            )
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0 if report.get("seed_count", 0) > 0 else 1
        report = close_run(args.if_root, args.run)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except Blocked as e:
        print(f"BLOCKED: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
