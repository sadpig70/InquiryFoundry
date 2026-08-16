#!/usr/bin/env python
"""One-shot stdout probe for live-notify vs exit-notify. Sleeps 5s."""
from __future__ import annotations

import time


def main() -> int:
    print("PAO_LIVE", flush=True)
    time.sleep(5)
    print("PAO_EXIT", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
