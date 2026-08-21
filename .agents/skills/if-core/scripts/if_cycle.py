#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from if_core.cycle import close_run, inquiry_cycle, rejudge  # noqa: E402
from if_core.review import (  # noqa: E402
    apply_recommendation,
    ratify,
    request_review,
    review_packet,
)
from if_core.store import Blocked, Store  # noqa: E402


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
    run.add_argument("--lwars", required=True, help="LWAR1:anthropic,LWAR2:openai,LWAR3:xai")
    run.add_argument("--pack", action="append", default=[], help="kind=path")
    run.add_argument("--pao", action="store_true", help="publish via PAO bus (publish_collect)")
    close = sub.add_parser("close")
    close.add_argument("--run", required=True)
    close.add_argument("--if-root")
    packet = sub.add_parser("review-packet", help="write the reviewer's inbox for a run")
    packet.add_argument("--run", required=True)
    packet.add_argument("--if-root")
    packet.add_argument("--out", required=True)
    packet.add_argument("--constraints-from",
                        help="brief.yaml whose constraints to apply (default: the run's own)")
    rec = sub.add_parser("recommend", help="fold a reviewer outbox into review.yaml")
    rec.add_argument("--run", required=True)
    rec.add_argument("--if-root")
    rec.add_argument("--outbox", required=True)
    rec.add_argument("--by", required=True, help="which reviewer produced it")
    ask = sub.add_parser("review-run", help="send a run to a reviewer LWAR and fold back its recommendation")
    ask.add_argument("--run", required=True)
    ask.add_argument("--if-root")
    ask.add_argument("--lwar-id", required=True)
    ask.add_argument("--by", required=True, help="which reviewer produced it")
    ask.add_argument("--timeout-s", type=int, default=1200)
    ask.add_argument("--no-apply", action="store_true",
                     help="collect the recommendation without touching review.yaml")
    ask.add_argument("--constraints-from",
                     help="brief.yaml whose constraints to apply (default: the run's own)")
    ask.add_argument("--round", type=int, default=None,
                     help="review round (default: next free one)")
    rej = sub.add_parser("rejudge", help="score questions a lost judge left unscored")
    rej.add_argument("--run", required=True)
    rej.add_argument("--if-root")
    rej.add_argument("--lwars", required=True, help="LWAR1:openai,LWAR2:google,LWAR3:xai")
    rej.add_argument("--timeout-s", type=int, default=None)
    rat = sub.add_parser("ratify", help="a person takes ownership of a recommendation")
    rat.add_argument("--run", required=True)
    rat.add_argument("--if-root")
    rat.add_argument("--reviewer", required=True)
    rat.add_argument("--delegated", action="store_true",
                     help="a standing delegation signs this; the machine made the call")
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
        store = Store(args.if_root)
        run_dir = store.root / "runs" / args.run
        def _constraints():
            src = getattr(args, "constraints_from", None)
            if not src:
                return None
            return list((yaml.safe_load(Path(src).read_text(encoding="utf-8"))
                         or {}).get("constraints") or [])

        if args.cmd == "review-packet":
            out = Path(args.out)
            out.parent.mkdir(parents=True, exist_ok=True)
            packet = review_packet(store, run_dir, _constraints())
            out.write_text(
                yaml.safe_dump(packet, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
            print(json.dumps({"wrote": str(out), "questions": len(packet["questions"])},
                             ensure_ascii=False, indent=2))
            return 0
        if args.cmd == "rejudge":
            print(json.dumps(
                rejudge(args.if_root, args.run, parse_lwars(args.lwars), args.timeout_s),
                ensure_ascii=False, indent=2))
            return 0
        if args.cmd == "review-run":
            print(json.dumps(
                request_review(store, run_dir, args.lwar_id, args.by,
                               args.timeout_s, apply=not args.no_apply,
                               constraints=_constraints(), round_n=args.round),
                ensure_ascii=False, indent=2))
            return 0
        if args.cmd == "recommend":
            outbox = yaml.safe_load(Path(args.outbox).read_text(encoding="utf-8"))
            print(json.dumps(apply_recommendation(run_dir, outbox, args.by),
                             ensure_ascii=False, indent=2))
            return 0
        if args.cmd == "ratify":
            print(json.dumps(ratify(run_dir, args.reviewer, args.delegated),
                             ensure_ascii=False, indent=2))
            return 0
        report = close_run(args.if_root, args.run)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except Blocked as e:
        print(f"BLOCKED: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
