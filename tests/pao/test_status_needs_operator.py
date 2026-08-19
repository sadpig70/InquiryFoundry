"""`oa status` must name the slots the operator has to nudge.

An exit-notify LWAR stops watching whenever its session's turn ends. The slot
stays `on`, so the registry still looks healthy and only the heartbeat age says
otherwise. Every field needed to spot that was already in the per-LWAR entries,
but reading it meant scanning each one by eye, and OA twice proposed a run
against a roster that had already gone quiet. The aggregate exists so that is a
lookup, not an act of vigilance.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OA = ROOT / ".agents" / "skills" / "pao-oa" / "scripts" / "oa.py"
sys.path.insert(0, str(ROOT / ".agents" / "skills" / "pao-oa"))

from pao_runtime.common import atomic_write_json, ensure_mailbox, utc_now  # noqa: E402

INST = "lwar-instance-" + "c" * 32


def _iso(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def _seed(root: Path, slots: dict) -> None:
    atomic_write_json(
        root / "var" / "registry" / "lwar_registry.json",
        {
            "schema_version": "pao.lwar-registry-state.v1",
            "registry_version": 3,
            "allocation_strategy": "lowest_available",
            "slots": {
                lwar: {
                    "instance_id": INST,
                    "generation": 1,
                    "state": spec["state"],
                    "profile": {
                        "runtime_name": "Unreported Runtime",
                        "model": "Unreported Model",
                        "adapter_id": "unreported_runtime",
                        "vendor_family": spec["vendor_family"],
                        "interface": "agent",
                        "capabilities": ["coding"],
                    },
                    "registered_at": _iso(datetime.now(timezone.utc) - timedelta(hours=2)),
                    "last_seen": None,
                }
                for lwar, spec in slots.items()
            },
            "updated_at": utc_now(),
        },
    )
    for lwar, spec in slots.items():
        ensure_mailbox(root, lwar)
        atomic_write_json(
            root / "mailbox" / lwar / "heartbeat.json",
            {
                "schema_version": "pao.heartbeat.v1",
                "lwar_id": lwar,
                "instance_id": INST,
                "generation": 1,
                "status": "watching",
                "last_seen": _iso(
                    datetime.now(timezone.utc) - timedelta(seconds=spec["age_s"])
                ),
                "current_task_id": None,
            },
        )


def _status(root: Path) -> dict:
    proc = subprocess.run(
        [sys.executable, str(OA), "status", "--root", str(root)],
        capture_output=True, text=True, check=True,
    )
    return json.loads(proc.stdout.strip().splitlines()[-1])


def test_stale_but_on_slots_are_listed_for_the_operator(tmp_path):
    _seed(tmp_path, {
        "LWAR1": {"state": "on", "vendor_family": "moonshot", "age_s": 5.0},
        "LWAR2": {"state": "on", "vendor_family": "deepseek", "age_s": 5000.0},
    })
    report = _status(tmp_path)
    assert report["routable_count"] == 1
    assert [x["lwar_id"] for x in report["needs_operator"]] == ["LWAR2"]
    entry = report["needs_operator"][0]
    assert entry["vendor_family"] == "deepseek"
    assert entry["runtime_status"] == "stale"
    assert entry["heartbeat_age_s"] > 4000


def test_a_slot_the_operator_turned_off_is_not_a_nudge(tmp_path):
    """`off` is a decision that was already made; only `on` slots are a surprise."""
    _seed(tmp_path, {
        "LWAR1": {"state": "off", "vendor_family": "alibaba", "age_s": 90000.0},
    })
    report = _status(tmp_path)
    assert report["needs_operator"] == []
    assert report["routable_count"] == 0


def test_healthy_roster_needs_nobody(tmp_path):
    _seed(tmp_path, {
        "LWAR1": {"state": "on", "vendor_family": "deepseek", "age_s": 1.0},
        "LWAR2": {"state": "on", "vendor_family": "moonshot", "age_s": 2.0},
        "LWAR3": {"state": "on", "vendor_family": "xai", "age_s": 3.0},
    })
    report = _status(tmp_path)
    assert report["needs_operator"] == []
    assert report["routable_count"] == 3
