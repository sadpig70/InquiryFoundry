"""Does HANDOFF section 7's index still match its sections?

The index exists because 22 thought-record sections accumulated corrections
inside their own bodies, so following a pointer from section 0 could land on a
sentence that a later section had already overturned. An index only helps while
it is complete: a section added without a row is invisible to the reader who
was told to start there, which is worse than having no index at all.

    python tools/check_handoff_index.py [--handoff HANDOFF.md]

Exit 1 on drift, so it can gate a commit.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SECTION = re.compile(r"^## (7\.\d+) (.+)$")
ROW = re.compile(r"^\| (7\.\d+) ([^|]*)\|\s*([^|]*?)\s*\|")
INDEX_HEAD = "## 7.0"
STATES = {"현행", "이관", "정정됨", "기록"}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--handoff", default="HANDOFF.md")
    args = ap.parse_args(argv)

    lines = Path(args.handoff).read_text(encoding="utf-8").splitlines()

    sections, rows, inside = [], {}, False
    for line in lines:
        m = SECTION.match(line)
        if m:
            if m.group(1) == "7.0":
                inside = True
                continue
            inside = False
            sections.append(m.group(1))
        if inside:
            r = ROW.match(line)
            if r and r.group(1) != "7.0":
                rows[r.group(1)] = r.group(3).strip()

    problems = []
    for sec in sections:
        if sec not in rows:
            problems.append("%s has no index row" % sec)
    for sec in rows:
        if sec not in sections:
            problems.append("%s is indexed but does not exist" % sec)
    for sec, state in rows.items():
        bare = state.replace("*", "").strip()
        if bare not in STATES:
            problems.append("%s state %r is not one of %s"
                            % (sec, bare, "/".join(sorted(STATES))))

    print("sections %d | indexed %d" % (len(sections), len(rows)))
    if problems:
        for p in problems:
            print("  DRIFT: %s" % p)
        return 1
    print("index matches")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
