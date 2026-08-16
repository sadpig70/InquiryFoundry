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
