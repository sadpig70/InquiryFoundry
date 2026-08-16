#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from if_core.schema import SchemaError, dump_schema, validate_obj  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="IF schema validator")
    p.add_argument("--kind", required=True)
    p.add_argument("path", nargs="?", help="yaml/json file")
    p.add_argument("--dump", action="store_true")
    args = p.parse_args()
    if args.dump:
        print(json.dumps(dump_schema(args.kind), indent=2))
        return 0
    if not args.path:
        print("path required", file=sys.stderr)
        return 2
    raw = Path(args.path).read_text(encoding="utf-8")
    data = yaml.safe_load(raw) if args.path.endswith((".yaml", ".yml")) else json.loads(raw)
    try:
        validate_obj(args.kind, data)
    except SchemaError as e:
        print(f"FAIL {args.kind}: {e}")
        return 1
    print(f"PASS {args.kind} {args.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
