"""P4 slot-lifecycle recovery: unadopted-slot reclaim and pending-control expiry.

Both paths exist because `retire_stale` and `reap_startup` each require a
current-generation heartbeat, and a slot that was approved but never adopted has
none — so neither could ever reach it. The fences below are the whole point of
the commands, so they are what these tests pin down.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".agents" / "skills" / "pao-lwar"))

from pao_runtime.common import atomic_write_json, ensure_mailbox, utc_now  # noqa: E402
from pao_runtime.registry import RegistryService  # noqa: E402

INST = "lwar-instance-" + "a" * 32
OTHER = "lwar-instance-" + "b" * 32


def _iso(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def _seed_registry(root: Path, lwar: str = "LWAR1", *, generation: int = 2,
                   instance_id: str = INST, registered_ago_s: float = 7200.0,
                   state: str = "on") -> None:
    registered_at = datetime.now(timezone.utc) - timedelta(seconds=registered_ago_s)
    atomic_write_json(
        root / "var" / "registry" / "lwar_registry.json",
        {
            "schema_version": "pao.lwar-registry-state.v1",
            "registry_version": 7,
            "allocation_strategy": "lowest_available",
            "slots": {
                lwar: {
                    "instance_id": instance_id,
                    "generation": generation,
                    "state": state,
                    "profile": {
                        "runtime_name": "Unreported Runtime",
                        "model": "Unreported Model",
                        "adapter_id": "unreported_runtime",
                        "vendor_family": "unreported_vendor",
                        "interface": "agent",
                        "capabilities": ["coding"],
                    },
                    "registered_at": _iso(registered_at),
                    "last_seen": None,
                }
            },
            "updated_at": utc_now(),
        },
    )
    ensure_mailbox(root, lwar)


def _write_heartbeat(root: Path, lwar: str, *, instance_id: str, generation: int,
                     status: str = "watching", age_s: float = 0.0) -> None:
    last_seen = datetime.now(timezone.utc) - timedelta(seconds=age_s)
    atomic_write_json(
        root / "mailbox" / lwar / "heartbeat.json",
        {
            "schema_version": "pao.heartbeat.v1",
            "lwar_id": lwar,
            "instance_id": instance_id,
            "generation": generation,
            "status": status,
            "last_seen": _iso(last_seen),
            "current_task_id": None,
        },
    )


def _write_control(root: Path, lwar: str, control_id: str, command: str = "shutdown",
                   age_s: float = 3600.0) -> Path:
    path = root / "mailbox" / lwar / "control" / f"{control_id}.json"
    atomic_write_json(
        path,
        {
            "schema_version": "pao.control.v1",
            "control_id": control_id,
            "lwar_id": lwar,
            "instance_id": INST,
            "generation": 2,
            "command": command,
            "task_id": None,
            "reason": "test",
            "registry_version": 7,
            "created_at": utc_now(),
        },
    )
    stamp = (datetime.now(timezone.utc) - timedelta(seconds=age_s)).timestamp()
    import os

    os.utime(path, (stamp, stamp))
    return path


# --- reclaim_unadopted -------------------------------------------------------


def test_reclaim_unadopted_frees_slot_and_tombstones_generation(tmp_path):
    _seed_registry(tmp_path)
    service = RegistryService(tmp_path)

    outcome = service.reclaim_unadopted("LWAR1", INST, 2, 60.0, "never adopted")

    assert outcome["accepted"] is True
    assert outcome["unadopted_confirmed"] is True
    assert outcome["approval_age_s"] > 60.0
    registry = json.loads((tmp_path / "var" / "registry" / "lwar_registry.json").read_text())
    assert "LWAR1" not in registry["slots"]
    assert registry["registry_version"] == 8
    tombstone = json.loads(
        (tmp_path / "var" / "registry" / "tombstones.json").read_text()
    )["entries"]["LWAR1"]
    assert tombstone["retirement_mode"] == "unadopted_reap"
    assert tombstone["last_generation"] == 2


def test_reclaim_unadopted_replay_is_idempotent(tmp_path):
    _seed_registry(tmp_path)
    service = RegistryService(tmp_path)
    first = service.reclaim_unadopted("LWAR1", INST, 2, 60.0, "never adopted")
    version_after_first = json.loads(
        (tmp_path / "var" / "registry" / "lwar_registry.json").read_text()
    )["registry_version"]

    second = service.reclaim_unadopted("LWAR1", INST, 2, 60.0, "never adopted")

    assert first["accepted"] is True
    assert second["accepted"] is True
    assert second["reason"] == "already_reclaimed"
    version_after_second = json.loads(
        (tmp_path / "var" / "registry" / "lwar_registry.json").read_text()
    )["registry_version"]
    assert version_after_second == version_after_first


def test_reclaim_unadopted_refuses_adopted_identity(tmp_path):
    """The core fence: a matching heartbeat proves the runtime did start."""
    _seed_registry(tmp_path)
    _write_heartbeat(tmp_path, "LWAR1", instance_id=INST, generation=2)
    service = RegistryService(tmp_path)

    outcome = service.reclaim_unadopted("LWAR1", INST, 2, 60.0, "never adopted")

    assert outcome["accepted"] is False
    assert outcome["reason"] == "identity_already_adopted"
    registry = json.loads((tmp_path / "var" / "registry" / "lwar_registry.json").read_text())
    assert "LWAR1" in registry["slots"]
    assert registry["registry_version"] == 7


def test_reclaim_unadopted_ignores_previous_generation_heartbeat(tmp_path):
    """A leftover heartbeat from a retired generation is not adoption evidence."""
    _seed_registry(tmp_path)
    _write_heartbeat(tmp_path, "LWAR1", instance_id=OTHER, generation=1)
    service = RegistryService(tmp_path)

    outcome = service.reclaim_unadopted("LWAR1", INST, 2, 60.0, "never adopted")

    assert outcome["accepted"] is True


def test_reclaim_unadopted_refuses_identity_mismatch(tmp_path):
    _seed_registry(tmp_path)
    service = RegistryService(tmp_path)

    assert service.reclaim_unadopted("LWAR1", OTHER, 2, 60.0, "x")["reason"] == "identity_mismatch"
    assert service.reclaim_unadopted("LWAR1", INST, 3, 60.0, "x")["reason"] == "identity_mismatch"


def test_reclaim_unadopted_refuses_recent_approval(tmp_path):
    _seed_registry(tmp_path, registered_ago_s=10.0)
    service = RegistryService(tmp_path)

    outcome = service.reclaim_unadopted("LWAR1", INST, 2, 3600.0, "too soon")

    assert outcome["accepted"] is False
    assert outcome["reason"] == "approval_too_recent"


def test_reclaim_unadopted_refuses_active_mailbox_work(tmp_path):
    _seed_registry(tmp_path)
    _write_control(tmp_path, "LWAR1", "control-" + "c" * 32)
    service = RegistryService(tmp_path)

    outcome = service.reclaim_unadopted("LWAR1", INST, 2, 60.0, "has work")

    assert outcome["accepted"] is False
    assert outcome["reason"] == "active_mailbox_work"
    assert outcome["active_work"] == {"control": 1}


# --- expire_pending_control --------------------------------------------------


def test_expire_pending_control_archives_and_unblocks_retire(tmp_path):
    """V7: the shutdown that blocked reclaiming its own dead watcher's slot."""
    _seed_registry(tmp_path)
    _write_heartbeat(tmp_path, "LWAR1", instance_id=INST, generation=2, age_s=30000.0)
    control_id = "control-" + "d" * 32
    _write_control(tmp_path, "LWAR1", control_id, age_s=30000.0)
    service = RegistryService(tmp_path)
    observed = json.loads((tmp_path / "mailbox" / "LWAR1" / "heartbeat.json").read_text())

    expiry = service.expire_pending_control("LWAR1", INST, 2, 600.0, "dead watcher")

    assert expiry["accepted"] is True
    assert [e["command"] for e in expiry["expired"]] == ["shutdown"]
    assert not list((tmp_path / "mailbox" / "LWAR1" / "control").glob("*.json"))
    archive = tmp_path / "mailbox" / "LWAR1" / "archive" / "control"
    assert (archive / f"{control_id}.json").is_file()
    assert (archive / f"{control_id}.expired.json").is_file()

    retire = service.retire_stale(
        "LWAR1", INST, 2, observed["last_seen"], 120.0, "stale idle after control expiry"
    )
    assert retire["accepted"] is True


def test_expire_pending_control_preserves_original_bytes(tmp_path):
    _seed_registry(tmp_path)
    control_id = "control-" + "e" * 32
    path = _write_control(tmp_path, "LWAR1", control_id, age_s=30000.0)
    before = path.read_bytes()
    service = RegistryService(tmp_path)

    service.expire_pending_control("LWAR1", INST, 2, 600.0, "dead watcher")

    archived = tmp_path / "mailbox" / "LWAR1" / "archive" / "control" / f"{control_id}.json"
    assert archived.read_bytes() == before


def test_expire_pending_control_refuses_live_watcher(tmp_path):
    """V8: a fresh matching heartbeat still claims these controls."""
    _seed_registry(tmp_path)
    _write_heartbeat(tmp_path, "LWAR1", instance_id=INST, generation=2, age_s=5.0)
    _write_control(tmp_path, "LWAR1", "control-" + "f" * 32, age_s=30000.0)
    service = RegistryService(tmp_path)

    outcome = service.expire_pending_control("LWAR1", INST, 2, 600.0, "dead watcher")

    assert outcome["accepted"] is False
    assert outcome["reason"] == "watcher_alive"
    assert len(list((tmp_path / "mailbox" / "LWAR1" / "control").glob("*.json"))) == 1


def test_expire_pending_control_skips_recent_controls(tmp_path):
    _seed_registry(tmp_path)
    _write_control(tmp_path, "LWAR1", "control-" + "0" * 32, age_s=5.0)
    service = RegistryService(tmp_path)

    outcome = service.expire_pending_control("LWAR1", INST, 2, 600.0, "dead watcher")

    assert outcome["accepted"] is True
    assert outcome["expired"] == []
    assert outcome["skipped"][0]["reason"] == "too_recent"
    assert len(list((tmp_path / "mailbox" / "LWAR1" / "control").glob("*.json"))) == 1


def test_expire_pending_control_refuses_identity_mismatch(tmp_path):
    _seed_registry(tmp_path)
    _write_control(tmp_path, "LWAR1", "control-" + "1" * 32, age_s=30000.0)
    service = RegistryService(tmp_path)

    outcome = service.expire_pending_control("LWAR1", OTHER, 2, 600.0, "wrong identity")

    assert outcome["accepted"] is False
    assert outcome["reason"] == "identity_mismatch"
    assert len(list((tmp_path / "mailbox" / "LWAR1" / "control").glob("*.json"))) == 1
