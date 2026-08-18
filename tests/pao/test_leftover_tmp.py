"""doctor --clear-leftover-tmp: crash debris removal, fenced by provable redundancy.

A hard power-off kills the process between atomic_write_json's temp write and
os.replace, so its finally never runs. The orphan makes doctor unhealthy, and
both roles are contracted to stop on that — so one inert file locks the bus and
nothing in the CLI could clear it. These tests pin the fence rather than the
happy path: the flag must delete only what is provably a duplicate, and must
keep anything that could be the last copy of something.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".agents" / "skills" / "pao-oa"))

from pao_runtime.common import atomic_write_json, ensure_mailbox  # noqa: E402
from pao_runtime.pao_cli import _clear_leftover_tmp, _leftover_tmp_verdict  # noqa: E402

INST = "lwar-instance-" + "a" * 32
OTHER = "lwar-instance-" + "b" * 32


def _heartbeat(instance_id: str = INST, generation: int = 2, last_seen: str = "2026-08-18T05:51:57.286903Z") -> dict:
    return {
        "schema_version": "pao.heartbeat.v1",
        "lwar_id": "LWAR1",
        "instance_id": instance_id,
        "generation": generation,
        "status": "watching",
        "last_seen": last_seen,
        "current_task_id": None,
    }


def _aged(path: Path) -> Path:
    stamp = time.time() - 3600
    os.utime(path, (stamp, stamp))
    return path


def _tmp(mailbox: Path, payload, name: str = ".pao-x6to70i8.tmp") -> Path:
    path = mailbox / name
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return _aged(path)


def _mailbox(tmp_path: Path) -> Path:
    ensure_mailbox(tmp_path, "LWAR1")
    return tmp_path / "mailbox" / "LWAR1"


def _clear(tmp_path: Path, leftovers: list[Path]):
    return _clear_leftover_tmp(tmp_path, leftovers, time.time() - 60, "oa")


# --- the one removable case -------------------------------------------------


def test_redundant_heartbeat_is_cleared(tmp_path):
    mailbox = _mailbox(tmp_path)
    atomic_write_json(mailbox / "heartbeat.json", _heartbeat())
    orphan = _tmp(mailbox, _heartbeat(last_seen="2026-08-18T05:52:02.435874Z"))

    cleared, preserved = _clear(tmp_path, [orphan])

    assert cleared == [str(orphan)]
    assert preserved == []
    assert not orphan.exists()
    # The committed heartbeat is untouched and still authoritative.
    assert json.loads((mailbox / "heartbeat.json").read_text())["last_seen"].endswith("57.286903Z")


def test_verdict_reason_is_recorded(tmp_path):
    mailbox = _mailbox(tmp_path)
    atomic_write_json(mailbox / "heartbeat.json", _heartbeat())
    orphan = _tmp(mailbox, _heartbeat())
    assert _leftover_tmp_verdict(orphan) == (True, "redundant_heartbeat")


# --- everything else must survive -------------------------------------------


def test_result_tmp_is_preserved(tmp_path):
    """The case that matters: a crash mid-result may hold the only copy."""
    mailbox = _mailbox(tmp_path)
    atomic_write_json(mailbox / "heartbeat.json", _heartbeat())
    orphan = _tmp(
        mailbox,
        {"schema_version": "pao.result.v1", "task_id": "task-x", "status": "succeeded"},
    )

    cleared, preserved = _clear(tmp_path, [orphan])

    assert cleared == []
    assert preserved[0]["reason"] == "not_a_heartbeat:pao.result.v1"
    assert orphan.exists()


def test_unparseable_tmp_is_preserved(tmp_path):
    mailbox = _mailbox(tmp_path)
    orphan = _tmp(mailbox, '{"schema_version": "pao.heartb')

    cleared, preserved = _clear(tmp_path, [orphan])

    assert cleared == []
    assert preserved[0]["reason"] == "unparseable"
    assert orphan.exists()


def test_heartbeat_without_committed_sibling_is_preserved(tmp_path):
    """No committed file means the temp may be the only surviving copy."""
    mailbox = _mailbox(tmp_path)
    orphan = _tmp(mailbox, _heartbeat())

    cleared, preserved = _clear(tmp_path, [orphan])

    assert cleared == []
    assert preserved[0]["reason"] == "no_committed_heartbeat"
    assert orphan.exists()


@pytest.mark.parametrize(
    "committed",
    [
        _heartbeat(instance_id=OTHER),
        _heartbeat(generation=3),
    ],
    ids=["instance_differs", "generation_differs"],
)
def test_identity_mismatch_is_preserved(tmp_path, committed):
    mailbox = _mailbox(tmp_path)
    atomic_write_json(mailbox / "heartbeat.json", committed)
    orphan = _tmp(mailbox, _heartbeat())

    cleared, preserved = _clear(tmp_path, [orphan])

    assert cleared == []
    assert preserved[0]["reason"] == "identity_differs_from_committed"
    assert orphan.exists()


def test_recent_tmp_is_preserved(tmp_path):
    """An in-flight atomic write that aged between scan and unlink."""
    mailbox = _mailbox(tmp_path)
    atomic_write_json(mailbox / "heartbeat.json", _heartbeat())
    fresh = mailbox / ".pao-fresh0001.tmp"
    fresh.write_text(json.dumps(_heartbeat()), encoding="utf-8")

    # Normal cutoff (now - 60): a file written just now is newer than it.
    cleared, preserved = _clear(tmp_path, [fresh])

    assert cleared == []
    assert preserved[0]["reason"] == "became_recent"
    assert fresh.exists()


def test_mixed_batch_clears_only_the_safe_one(tmp_path):
    mailbox = _mailbox(tmp_path)
    atomic_write_json(mailbox / "heartbeat.json", _heartbeat())
    safe = _tmp(mailbox, _heartbeat(), ".pao-safe0001.tmp")
    unsafe = _tmp(
        mailbox,
        {"schema_version": "pao.task.v1", "task_id": "task-y"},
        ".pao-unsafe001.tmp",
    )

    cleared, preserved = _clear(tmp_path, [safe, unsafe])

    assert cleared == [str(safe)]
    assert [p["path"] for p in preserved] == [str(unsafe)]
    assert not safe.exists()
    assert unsafe.exists()


def test_cleanup_is_audited(tmp_path):
    mailbox = _mailbox(tmp_path)
    atomic_write_json(mailbox / "heartbeat.json", _heartbeat())
    orphan = _tmp(mailbox, _heartbeat())

    _clear(tmp_path, [orphan])

    events = (tmp_path / "var" / "audit" / "events.jsonl").read_text(encoding="utf-8")
    assert "leftover_tmp_cleared" in events
