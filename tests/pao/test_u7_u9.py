"""U7 cancel-tombstone ledger close; U9 retry outbox isolation."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".agents" / "skills" / "pao-lwar"))

from pao_runtime.common import atomic_write_json, ensure_mailbox, utc_now  # noqa: E402
from pao_runtime.transport import FileTransport  # noqa: E402


def _task(tmp: Path, lwar: str, task_id: str) -> dict:
    jail = tmp / "jail"
    jail.mkdir(exist_ok=True)
    inst = "a" * 32
    return {
        "schema_version": "pao.task.v1",
        "task_id": task_id,
        "workflow_id": "workflow-if-run-u7",
        "depends_on": [],
        "lwar_id": lwar,
        "instance_id": f"lwar-instance-{inst}",
        "generation": 1,
        "registry_version": 1,
        "goal": "test",
        "instructions": "x",
        "completion_criteria": ["y"],
        "cwd": str(jail),
        "timeout_s": 60,
        "permissions": {"read": [str(jail)], "write": [str(jail)], "network": False},
        "max_retries": 2,
        "priority": 5,
        "attempt": 1,
        "created_at": utc_now(),
    }


def test_finalize_cancel_incoming_submits_cancelled(tmp_path):
    lwar = "LWAR1"
    task_id = "task-if-RUN-u7-contrarian-LWAR1-r1"
    transport = FileTransport(tmp_path)
    mailbox = ensure_mailbox(tmp_path, lwar)
    task = _task(tmp_path, lwar, task_id)
    incoming = mailbox / "incoming" / f"005_{task_id}.json"
    atomic_write_json(incoming, task)
    transport.write_cancel_tombstone(
        {"lwar_id": lwar, "instance_id": task["instance_id"], "generation": 1, "registry_version": 1},
        task_id,
        "control-test",
    )
    action = transport.finalize_cancel_tombstone(lwar, task_id)
    assert action == "cancelled"
    assert transport.result_exists(lwar, task_id)
    outgoing = mailbox / "outgoing" / f"{task_id}.result.json"
    result = json.loads(outgoing.read_text(encoding="utf-8"))
    assert result["status"] == "cancelled"
    assert not incoming.exists()
    assert not (mailbox / "cancelled" / f"{task_id}.json").exists()


def test_finalize_missing_pending_is_absent(tmp_path):
    transport = FileTransport(tmp_path)
    ensure_mailbox(tmp_path, "LWAR1")
    transport.write_cancel_tombstone(
        {
            "lwar_id": "LWAR1",
            "instance_id": "lwar-instance-" + "b" * 32,
            "generation": 1,
            "registry_version": 1,
        },
        "task-orphan-cancel",
        None,
    )
    assert transport.finalize_cancel_tombstone("LWAR1", "task-orphan-cancel") == "tombstone_pending_absent"
