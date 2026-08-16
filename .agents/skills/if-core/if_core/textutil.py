from __future__ import annotations

import re
import unicodedata


def normalize_tokens(text: str) -> str:
    """Jaccard tokens. Hangul: overlapping 2-char slices (동시에 → 동시 시에)."""
    text = unicodedata.normalize("NFC", text or "").lower()
    text = re.sub(r"[^\w\s가-힣]", " ", text, flags=re.UNICODE)
    parts: list[str] = []
    for tok in text.split():
        hangul = re.fullmatch(r"[가-힣]+", tok)
        if hangul and len(tok) >= 2:
            parts.extend(tok[i : i + 2] for i in range(len(tok) - 1))
        else:
            parts.append(tok)
    return " ".join(parts)


def token_set(seed: dict) -> set[str]:
    return set((seed.get("question_norm") or "").split())


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)
