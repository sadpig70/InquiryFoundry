#!/usr/bin/env python
"""Dispatch IF role after visibility check. complete uses --result-file only."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

_here = Path(__file__).resolve()
# if-lwar/scripts -> if-lwar -> skills / if-core
_CORE = _here.parents[1].parent / "if-core"
if not (_CORE / "if_core").is_dir():
    print(f"if_core missing next to if-lwar: {_CORE}", file=sys.stderr)
    raise SystemExit(2)
sys.path.insert(0, str(_CORE))

from if_core.bus import assert_visible  # noqa: E402
from if_core.contrarian import cross_examine  # noqa: E402
from if_core.generate import generate  # noqa: E402
from if_core.judge import judge  # noqa: E402
from if_core.semantic import SemanticError, assert_role_output  # noqa: E402


def self_test() -> int:
    if not (_CORE / "if_core").is_dir():
        print(json.dumps({"ok": False, "error": "if-core missing"}))
        return 2
    src = Path(__file__).read_text(encoding="utf-8")
    needle = "Path(" + "r\"D:"
    if needle in src:
        print(json.dumps({"ok": False, "error": "machine-absolute import path"}))
        return 2
    from if_core import bus, contrarian, generate as gen, judge as jdg  # noqa: F401

    print(json.dumps({"ok": True, "core": str(_CORE)}))
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--inbox")
    p.add_argument("--outbox")
    p.add_argument("--jail")
    p.add_argument("--role")
    p.add_argument("--lwar-id")
    p.add_argument("--stub", action="store_true", help="use deterministic role stubs")
    p.add_argument(
        "--validate-only",
        action="store_true",
        help="validate an existing outbox (live AI_ path); do not run stubs",
    )
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args()
    if args.self_test:
        return self_test()
    if not all([args.inbox, args.outbox, args.jail, args.role, args.lwar_id]):
        print("inbox/outbox/jail/role/lwar-id required", file=sys.stderr)
        return 2
    inbox_path = Path(args.inbox)
    outbox_path = Path(args.outbox)
    try:
        assert_visible(args.lwar_id, args.role, str(inbox_path), Path(args.jail))
    except PermissionError as e:
        print(f"protocol_error: {e}", file=sys.stderr)
        return 3
    inbox = yaml.safe_load(inbox_path.read_text(encoding="utf-8")) or {}
    inbox["lwar_id"] = args.lwar_id
    stub = bool(args.stub or inbox.get("stub") or (inbox.get("adapter_options") or {}).get("if_stub"))
    dropped = 0
    if args.validate_only:
        if not outbox_path.is_file():
            print("validate-only: outbox missing", file=sys.stderr)
            return 2
        out = yaml.safe_load(outbox_path.read_text(encoding="utf-8"))
    elif stub:
        if args.role == "generate":
            out = generate(inbox, hint_dir=Path(args.jail) / "hints")
        elif args.role == "contrarian":
            out = cross_examine(inbox)
        elif args.role == "judge":
            out = judge(inbox)
        elif args.role == "review":
            print("review has no stub: a recommendation must be reasoned",
                  file=sys.stderr)
            return 2
        else:
            print("unknown role", file=sys.stderr)
            return 2
    else:
        print(
            "live path: write outbox via role SKILL (AI_), then rerun with --validate-only",
            file=sys.stderr,
        )
        return 2
    try:
        assert_role_output(args.role, out, allow_stub=stub)
    except SemanticError as e:
        print(f"semantic_error: {e}", file=sys.stderr)
        return 4
    outbox_path.parent.mkdir(parents=True, exist_ok=True)
    outbox_path.write_text(yaml.safe_dump(out, allow_unicode=True, sort_keys=False), encoding="utf-8")
    n = len(out) if isinstance(out, list) else 0
    print(json.dumps({"seeds": n, "dropped": dropped, "role": args.role, "stub": stub}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
