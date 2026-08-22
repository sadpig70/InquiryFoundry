"""Shape-plus-content gates for live role outboxes. Stub runs opt in explicitly."""
from __future__ import annotations

import re

STUB_MARKERS = ("deterministic stub",)
# leftover template holes, not the Hangul letter 가/나 used in operator stems
PLACEHOLDER_RE = re.compile(r"\b(TBD|TODO|FIXME|placeholder)\b|\b원리 X\b", re.I)


class SemanticError(ValueError):
    pass


# Figures with a unit attached: the shape that leaked. A reason saying a
# question pre-decided its answer "at public experiment scale (C 1e18~1e21)"
# is a sound verdict, and RUN-20260822-live10g's generator took the range as
# its working envelope. Numbers that ARE the defect stay legal behind the
# marker below, because "the criterion says 5% and the falsifier says 15%" is
# the finding itself.
FIGURE_RE = re.compile(
    r"\b\d+(?:[.,]\d+)?\s*(?:e\s*[+-]?\d+)?\s*"
    r"(?:FLOPs?|플롭|GPU|TPU|시간|hours?|days?|달러|USD|\$|원|억|조|"
    r"토큰|tokens?|epochs?|에폭|파라미터|params?|B|M|K)\b"
    r"|\b\d+\s*[eE]\d+\b|10\^\{?\d+",
)
# The reviewer says outright that the figure is the defect.
FIGURE_OK = "[figure-is-the-defect]"


def figure_leak(text: str) -> str | None:
    """The first unit-bearing figure in a reason, or None."""
    if FIGURE_OK in text:
        return None
    m = FIGURE_RE.search(text)
    return m.group(0).strip() if m else None


def _blob(item: dict) -> str:
    bits = [str(item.get("question") or ""), str(item.get("attack") or ""),
            str(item.get("rationale") or ""), str(item.get("notes") or "")]
    for a in item.get("attacks") or []:
        bits.append(str(a.get("attack") or ""))
        bits.append(str(a.get("rationale") or ""))
    return " ".join(bits)


def assert_role_output(role: str, items, *, allow_stub: bool) -> None:
    if role == "review":
        # A reviewer answers about the whole run at once, so its outbox is a
        # mapping, not the per-item list the other roles return.
        if not isinstance(items, dict):
            raise SemanticError("review outbox must be a YAML mapping")
        recs = items.get("recommendations")
        if not isinstance(recs, list) or not recs:
            raise SemanticError("review outbox has no recommendations")
        if allow_stub:
            return
        for i, rec in enumerate(recs):
            if not isinstance(rec, dict):
                raise SemanticError(f"review[{i}] not an object")
            reason = str(rec.get("reason") or "")
            text = f"{reason} {rec.get('question_id') or ''}"
            if any(m in text.lower() for m in STUB_MARKERS):
                raise SemanticError(f"review[{i}] contains stub marker")
            if PLACEHOLDER_RE.search(text):
                raise SemanticError(f"review[{i}] contains placeholder")
            # A verdict with no argument is the failure mode that matters here:
            # the reason becomes the next run's avoid_pattern.
            if rec.get("decision") in {"reject", "defer"} and len(reason.strip()) < 20:
                raise SemanticError(f"review[{i}] {rec.get('decision')} without a reason")
            # A rejection is fed forward as something to avoid asking, so one
            # grounded in what this installation happens to own has to declare
            # itself. Absent means the verdict is about the question.
            if rec.get("reason_kind") not in (None, "question_defect", "our_capacity"):
                raise SemanticError(f"review[{i}] unknown reason_kind {rec['reason_kind']!r}")
            kind = rec.get("reason_kind") or (
                "our_capacity" if rec.get("decision") == "defer" else "question_defect")
            if rec.get("decision") == "reject" and kind == "question_defect":
                pattern = str(rec.get("pattern") or "").strip()
                if len(pattern) < 10:
                    raise SemanticError(
                        f"review[{i}] question_defect reject needs a pattern line")
                leak = figure_leak(pattern)
                if leak:
                    raise SemanticError(
                        f"review[{i}] pattern carries a figure ({leak}); "
                        "patterns name the structure of a defect, not its numbers")
            leak = figure_leak(reason)
            if leak and rec.get("decision") in {"reject", "defer"}:
                raise SemanticError(
                    f"review[{i}] reason carries a figure ({leak}); write it as structure, "
                    f"or mark it {FIGURE_OK} when the figure is the defect")
        return
    if not isinstance(items, list):
        raise SemanticError(f"{role} outbox must be a YAML list")
    if len(items) == 0:
        raise SemanticError(f"{role} outbox is empty")
    if allow_stub:
        return
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            raise SemanticError(f"{role}[{i}] not an object")
        text = _blob(item)
        if any(m in text.lower() for m in STUB_MARKERS):
            raise SemanticError(f"{role}[{i}] contains stub marker")
        if PLACEHOLDER_RE.search(text):
            raise SemanticError(f"{role}[{i}] contains placeholder")
        if role == "contrarian":
            attacks = item.get("attacks") or []
            rats = [str(a.get("rationale") or "") for a in attacks]
            if len(rats) >= 6 and len(set(rats)) == 1:
                raise SemanticError(f"{role}[{i}] identical rationale x6")
