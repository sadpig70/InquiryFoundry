from __future__ import annotations

from .const import LEGAL, PHASE2_ALLOWED_FROM


class TransitionError(ValueError):
    pass


def assert_transition(old: str, new: str, actor: str, reviewer_ok: bool = False) -> None:
    if actor == "phase2":
        if old not in PHASE2_ALLOWED_FROM or new != "QUARANTINE":
            raise TransitionError("illegal phase2 transition")
        return
    if new not in LEGAL[old]:
        raise TransitionError(f"illegal {old}->{new}")
    if new == "ADOPTED" and not (actor == "human" and reviewer_ok):
        raise TransitionError("ADOPTED requires human reviewer")
