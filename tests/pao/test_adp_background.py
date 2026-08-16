"""Arg and CLI surface for ADP --background / --report-every."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".agents" / "skills" / "pao-lwar"))

from pao_runtime.adp_watch import build_parser, validate_watch_args  # noqa: E402

WATCH = ROOT / ".agents" / "skills" / "pao-lwar" / "scripts" / "adp_watch.py"
LWAR = ROOT / ".agents" / "skills" / "pao-lwar" / "scripts" / "lwar.py"


def _ns(**overrides) -> argparse.Namespace:
    base = dict(
        interval=5.0,
        timeout=90.0,
        lease_seconds=180,
        resident=False,
        background=False,
        report_every=86400.0,
        state_wait_backoff_max=None,
        detach=False,
        stop=False,
        max_runtime_s=None,
    )
    base.update(overrides)
    return argparse.Namespace(**base)


def test_report_every_default_is_24h() -> None:
    args = build_parser().parse_args(["--identity-file", "x", "--background"])
    assert args.background is True
    assert args.report_every == 86400.0


def test_resident_and_background_conflict() -> None:
    with pytest.raises(SystemExit, match="mutually exclusive"):
        validate_watch_args(_ns(resident=True, background=True))


def test_report_every_must_be_positive() -> None:
    with pytest.raises(SystemExit, match="report-every"):
        validate_watch_args(_ns(background=True, report_every=0))


def test_cli_rejects_both_flags() -> None:
    p = subprocess.run(
        [
            sys.executable,
            str(WATCH),
            "--identity-file",
            "x",
            "--resident",
            "--background",
        ],
        capture_output=True,
        text=True,
    )
    assert p.returncode != 0
    assert "mutually exclusive" in (p.stderr + p.stdout)


def test_max_runtime_must_be_positive() -> None:
    with pytest.raises(SystemExit, match="max-runtime"):
        validate_watch_args(_ns(max_runtime_s=0))


def test_cli_help_lists_max_runtime() -> None:
    p = subprocess.run(
        [sys.executable, str(WATCH), "--help"],
        capture_output=True,
        text=True,
    )
    assert "--max-runtime-s" in p.stdout


def test_detach_requires_background() -> None:
    with pytest.raises(SystemExit, match="detach requires"):
        validate_watch_args(_ns(detach=True, background=False))


def test_cli_help_lists_detach_and_stop() -> None:
    p = subprocess.run(
        [sys.executable, str(WATCH), "--help"],
        capture_output=True,
        text=True,
    )
    assert p.returncode == 0
    assert "--detach" in p.stdout
    assert "--stop" in p.stdout


def test_recycle_requires_identity() -> None:
    recycle = ROOT / ".agents" / "skills" / "pao-lwar" / "scripts" / "kimi_adp_recycle.py"
    env = os.environ.copy()
    env.pop("PAO_LWAR_IDENTITY", None)
    p = subprocess.run(
        [sys.executable, str(recycle), "--recycle-s", "1"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert p.returncode != 0
    assert "identity" in (p.stderr + p.stdout).lower()


def test_lwar_response_help_lists_background() -> None:
    p = subprocess.run(
        [sys.executable, str(LWAR), "response", "--help"],
        capture_output=True,
        text=True,
    )
    assert p.returncode == 0
    assert "--background" in p.stdout
    assert "--report-every" in p.stdout
    assert "--detach" in p.stdout
    assert "--max-runtime-s" in p.stdout
    assert "--resident" in p.stdout


def test_notify_namespace_flags() -> None:
    from pao_runtime.adp_watch import (
        EXIT_NOTIFY_MAX_RUNTIME_S,
        exit_notify_namespace,
        live_notify_namespace,
    )

    exit_ns = exit_notify_namespace("x")
    assert exit_ns.resident is True
    assert exit_ns.background is False
    assert exit_ns.max_runtime_s == EXIT_NOTIFY_MAX_RUNTIME_S == 3000.0
    live_ns = live_notify_namespace("x")
    assert live_ns.resident is False
    assert live_ns.background is True
    assert live_ns.max_runtime_s is None
    assert live_ns.detach is False


def test_typed_watcher_scripts_require_identity() -> None:
    env = os.environ.copy()
    env.pop("PAO_LWAR_IDENTITY", None)
    for name in ("adp_exit_notify.py", "adp_live_notify.py"):
        script = ROOT / ".agents" / "skills" / "pao-lwar" / "scripts" / name
        p = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            env=env,
        )
        assert p.returncode != 0, name
        assert "identity" in (p.stderr + p.stdout).lower(), name


def test_lwar_adp_exit_and_live_help() -> None:
    from pao_runtime.lwar_cli import build_parser

    for verb in ("adp", "adp-exit", "adp-kimi"):
        p = subprocess.run(
            [sys.executable, str(LWAR), verb, "--help"],
            capture_output=True,
            text=True,
        )
        assert p.returncode == 0, verb
        assert "--max-runtime-s" in p.stdout
    live = subprocess.run(
        [sys.executable, str(LWAR), "adp-live", "--help"],
        capture_output=True,
        text=True,
    )
    assert live.returncode == 0
    assert "--identity-file" in live.stdout
    args = build_parser().parse_args(["adp-live", "--identity-file", "x"])
    assert args.handler.__name__ == "command_adp_live"


def test_lwar_adp_kimi_help_and_default() -> None:
    from pao_runtime.lwar_cli import ADP_MAX_RUNTIME_S, KIMI_MAX_RUNTIME_S, build_parser

    for verb in ("adp", "adp-kimi"):
        p = subprocess.run(
            [sys.executable, str(LWAR), verb, "--help"],
            capture_output=True,
            text=True,
        )
        assert p.returncode == 0, verb
        assert "--max-runtime-s" in p.stdout
        args = build_parser().parse_args([verb, "--identity-file", "x"])
        assert args.max_runtime_s == ADP_MAX_RUNTIME_S
    assert ADP_MAX_RUNTIME_S == KIMI_MAX_RUNTIME_S == 3000.0


def test_adp_kimi_requires_identity() -> None:
    env = os.environ.copy()
    env.pop("PAO_LWAR_IDENTITY", None)
    for verb in ("adp", "adp-kimi"):
        p = subprocess.run(
            [sys.executable, str(LWAR), verb],
            capture_output=True,
            text=True,
            env=env,
        )
        assert p.returncode != 0, verb
        assert "identity" in (p.stderr + p.stdout).lower()


def test_response_resident_max_runtime_while_pending(tmp_path: Path) -> None:
    req = "lwar-reg-" + ("ab" * 16)
    p = subprocess.run(
        [
            sys.executable,
            str(LWAR),
            "response",
            req,
            "--root",
            str(tmp_path),
            "--resident",
            "--max-runtime-s",
            "0.35",
            "--interval",
            "0.05",
            "--timeout",
            "1",
        ],
        capture_output=True,
        text=True,
    )
    assert p.returncode == 2
    assert "registration_pending" in p.stdout
    assert "max_runtime" in p.stdout
    assert "restart_response" in p.stdout


def test_resident_max_runtime_exits_idle(tmp_path: Path) -> None:
    from pao_runtime.common import atomic_write_json, ensure_mailbox, utc_now

    inst = "lwar-instance-" + ("ab" * 16)
    now = utc_now()
    identity = {
        "schema_version": "pao.lwar-identity.v1",
        "lwar_id": "LWAR1",
        "instance_id": inst,
        "generation": 1,
        "registry_version": 1,
        "state": "on",
        "behavior_contract": "lwar-runtime.v2-adp",
        "profile": {},
        "bus_root": str(tmp_path),
        "adopted_at": now,
    }
    registry = {
        "schema_version": "pao.lwar-registry-state.v1",
        "registry_version": 1,
        "allocation_strategy": "lowest_available",
        "slots": {
            "LWAR1": {
                "instance_id": inst,
                "generation": 1,
                "state": "on",
                "profile": {},
                "registered_at": now,
            }
        },
        "updated_at": now,
    }
    (tmp_path / "var" / "identities").mkdir(parents=True)
    (tmp_path / "var" / "registry").mkdir(parents=True)
    id_path = tmp_path / "var" / "identities" / f"{inst}.json"
    atomic_write_json(id_path, identity)
    atomic_write_json(tmp_path / "var" / "registry" / "lwar_registry.json", registry)
    ensure_mailbox(tmp_path, "LWAR1")
    p = subprocess.run(
        [
            sys.executable,
            str(WATCH),
            "--identity-file",
            str(id_path),
            "--root",
            str(tmp_path),
            "--resident",
            "--max-runtime-s",
            "0.4",
            "--interval",
            "0.05",
            "--timeout",
            "1",
        ],
        capture_output=True,
        text=True,
    )
    assert p.returncode == 10
    assert '"event": "idle_timeout"' in p.stdout or '"event":"idle_timeout"' in p.stdout
    assert "max_runtime" in p.stdout
    assert "restart_watcher" in p.stdout
