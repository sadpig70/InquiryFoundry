"""Shape-plus-content gates for live role outboxes. Stub runs opt in explicitly."""
from __future__ import annotations

import re

STUB_MARKERS = ("deterministic stub",)
# leftover template holes, not the Hangul letter 가/나 used in operator stems
PLACEHOLDER_RE = re.compile(r"\b(TBD|TODO|FIXME|placeholder)\b|\b원리 X\b", re.I)


class SemanticError(ValueError):
    pass


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
