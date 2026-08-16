from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Any

from . import audit
from .common import emit, load_json, require_local_filesystem, resolve_identity_root, resolve_root, utc_now
from .contracts import validate_contract
from .transport import FileTransport


def load_verified_identity(root: Path, identity_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    identity = load_json(identity_path)
    validate_contract(identity, "identity.schema.json")
    registry_path = root / "var" / "registry" / "lwar_registry.json"
    if not registry_path.is_file():
        # A missing --root/PAO_ROOT resolves to the cwd and lands here looking
        # like a bus fault — name the resolved root so the trap is visible.
        raise ValueError(
            f"dynamic registry does not exist under {root} — "
            "verify --root (or PAO_ROOT) points at the bus root"
        )
    registry = load_json(registry_path)
    validate_contract(registry, "registry-state.schema.json")
    slot = registry.get("slots", {}).get(identity["lwar_id"])
    if slot is None:
        raise ValueError("LWAR is not registered")
    if slot["instance_id"] != identity["instance_id"] or slot["generation"] != identity["generation"]:
        raise ValueError("LWAR identity tuple does not match registry")
    return identity, slot


def validate_watch_args(args: argparse.Namespace) -> None:
    """Validate watcher timing arguments for both CLI entry paths."""
    if args.interval <= 0 or args.timeout <= 0 or args.lease_seconds <= 0:
        raise SystemExit("interval, timeout, and lease-seconds must be positive")
    if args.interval > args.timeout:
        raise SystemExit("--interval must be <= --timeout (a longer interval would overshoot the slice)")
    if args.state_wait_backoff_max is not None and args.state_wait_backoff_max < args.interval:
        raise SystemExit("--state-wait-backoff-max must be >= --interval")
    resident = bool(getattr(args, "resident", False))
    background = bool(getattr(args, "background", False))
    if resident and background:
        raise SystemExit("--resident and --background are mutually exclusive")
    if bool(getattr(args, "detach", False)) and not background:
        raise SystemExit("--detach requires --background")
    report_every = getattr(args, "report_every", None)
    if report_every is not None and report_every <= 0:
        raise SystemExit("--report-every must be positive")
    max_runtime_s = getattr(args, "max_runtime_s", None)
    if max_runtime_s is not None and max_runtime_s <= 0:
        raise SystemExit("--max-runtime-s must be positive")


def _background(args: argparse.Namespace) -> bool:
    return bool(getattr(args, "background", False))


def _cross_idle_slices(args: argparse.Namespace) -> bool:
    return bool(getattr(args, "resident", False) or _background(args))


def _stay_after_delivery(args: argparse.Namespace, *, control_command: str | None = None) -> bool:
    """Background watchers keep the process; they only exit on fatal/stop controls."""
    if not _background(args):
        return False
    return control_command not in {"shutdown", "retire"}


def deliver_task(
    root: Path,
    transport: FileTransport,
    identity: dict[str, Any],
    identity_path: Path,
    task: dict[str, Any],
    claimed_path: Path,
    invocation: dict[str, Any],
    *,
    recovered_claim: bool,
) -> int:
    """Emit one identity-fenced task delivery, including safe redelivery."""
    with transport.invocation_delivery_guard(identity, invocation) as current:
        if not current:
            audit.record(
                root,
                "adp",
                {
                    "event": "invocation_superseded",
                    "lwar_id": identity["lwar_id"],
                    "task_id": task["task_id"],
                    "invocation_id": invocation["invocation_id"],
                },
            )
            emit(
                {
                    "event": "invocation_superseded",
                    "lwar_id": identity["lwar_id"],
                    "identity_file": str(identity_path),
                    "invocation_id": invocation["invocation_id"],
                    "invocation_epoch": invocation["epoch"],
                    "action": "stop_this_invocation",
                }
            )
            return 40
        transport.write_heartbeat(identity, "running", task["task_id"])
        audit.record(
            root,
            "adp",
            {
                "event": "task_redelivered" if recovered_claim else "task_received",
                "lwar_id": identity["lwar_id"],
                "task_id": task["task_id"],
                "invocation_id": invocation["invocation_id"],
                "invocation_epoch": invocation["epoch"],
            },
        )
        event = {
            "event": "task_received",
            "lwar_id": identity["lwar_id"],
            "task_id": task["task_id"],
            "identity_file": str(identity_path),
            "message_file": str(claimed_path),
            "task": task,
            "invocation_id": invocation["invocation_id"],
            "invocation_epoch": invocation["epoch"],
            "action": (
                "begin_then_execute_then_submit_result"
                if task.get("execution_id")
                else "execute_then_submit_result"
            ),
        }
        if task.get("execution_id"):
            event["execution_id"] = task["execution_id"]
        if recovered_claim:
            event["recovered_claim"] = True
        emit(event)
        return 0


def watch(args: argparse.Namespace) -> int:
    root = resolve_root(args.root)
    identity_path = Path(args.identity_file).resolve()
    audit_root: Path | None = None
    try:
        identity_snapshot = load_json(identity_path)
        validate_contract(identity_snapshot, "identity.schema.json")
        root = resolve_identity_root(identity_snapshot, identity_path, args.root)
        require_local_filesystem(root)
        audit_root = root
        transport = FileTransport(root)
        identity, slot = load_verified_identity(root, identity_path)
        from .detach import watcher_pid_path, write_pid_record

        write_pid_record(
            watcher_pid_path(root, identity["lwar_id"]),
            {
                "pid": os.getpid(),
                "lwar_id": identity["lwar_id"],
                "identity_file": str(identity_path),
                "started_at": utc_now(),
            },
        )
        invocation = transport.start_invocation(identity)
        audit.record(
            root,
            "adp",
            {
                "event": "invocation_started",
                "lwar_id": identity["lwar_id"],
                "invocation_id": invocation["invocation_id"],
                "invocation_epoch": invocation["epoch"],
            },
        )
    except Exception as error:
        # Never write an error record to an explicit/env root that conflicts
        # with the adopted identity. Until root binding succeeds, stdout is the
        # only safe error channel.
        if audit_root is not None:
            audit.record(audit_root, "adp", {"event": "adp_error", "error": str(error)})
        emit(
            {
                "event": "adp_error",
                "error": str(error),
                "identity_file": str(identity_path),
                "action": "stop",
            }
        )
        return 30
    deadline = time.monotonic() + args.timeout
    wait_s = args.interval
    consecutive_errors = 0
    started = time.monotonic()
    report_every = float(getattr(args, "report_every", 86400.0) or 86400.0)
    next_report = started + report_every
    notified_task_id: str | None = None
    max_runtime_s = getattr(args, "max_runtime_s", None)

    while True:
        now = time.monotonic()
        if max_runtime_s is not None and (now - started) >= float(max_runtime_s):
            emit(
                {
                    "event": "idle_timeout",
                    "lwar_id": identity["lwar_id"],
                    "identity_file": str(identity_path),
                    "waited_s": round(now - started, 3),
                    "reason": "max_runtime",
                    "action": "restart_watcher",
                }
            )
            return 10
        if now >= deadline:
            if _cross_idle_slices(args):
                # Cross the idle slice boundary inside the same watcher
                # process. The next poll re-verifies identity/registry state
                # and refreshes heartbeat, so agent scheduling latency cannot
                # turn a live resident session into a stale LWAR.
                deadline = now + args.timeout
                wait_s = args.interval
                consecutive_errors = 0
                continue
            break
        try:
            identity, slot = load_verified_identity(root, identity_path)
        except Exception as error:
            # Identity no longer verifies (revoked, generation bump, gone) — a
            # genuinely fatal condition. Stop and report.
            audit.record(root, "adp", {"event": "adp_error", "error": str(error)})
            emit(
                {
                    "event": "adp_error",
                    "error": str(error),
                    "identity_file": str(identity_path),
                    "action": "stop",
                }
            )
            return 30

        try:
            control = transport.claim_control(identity)
            if control is not None:
                with transport.invocation_delivery_guard(identity, invocation) as current:
                    if not current:
                        emit(
                            {
                                "event": "invocation_superseded",
                                "lwar_id": identity["lwar_id"],
                                "identity_file": str(identity_path),
                                "invocation_id": invocation["invocation_id"],
                                "invocation_epoch": invocation["epoch"],
                                "action": "stop_this_invocation",
                            }
                        )
                        return 40
                    transport.write_heartbeat(identity, "control", None)
                    # A cancel carrying a task_id is persisted as a tombstone BEFORE
                    # the event reaches the agent, so cancellation of a not-yet-
                    # claimed task no longer depends on the agent remembering it.
                    if control.get("command") == "cancel" and control.get("task_id"):
                        transport.write_cancel_tombstone(
                            identity, control["task_id"], control.get("control_id")
                        )
                    audit.record(
                        root,
                        "adp",
                        {
                            "event": "control",
                            "lwar_id": identity["lwar_id"],
                            "command": control.get("command"),
                            "control_id": control.get("control_id"),
                            "invocation_id": invocation["invocation_id"],
                        },
                    )
                    # ping is heartbeat-only in background mode — do not wake the agent.
                    emit_control = not (
                        _background(args) and control.get("command") == "ping"
                    )
                    if emit_control:
                        emit(
                            {
                                "event": "control",
                                "command": control.get("command"),
                                "identity_file": str(identity_path),
                                "message": control,
                                "invocation_id": invocation["invocation_id"],
                                "invocation_epoch": invocation["epoch"],
                            }
                        )
                    try:
                        transport.ack_control(identity, control)
                    except (OSError, TimeoutError) as error:
                        # Delivery already reached stdout. Leave control_claimed in
                        # place for at-least-once redelivery on the next slice.
                        audit.record(
                            root,
                            "adp",
                            {"event": "control_ack_failed", "error": str(error), "control_id": control.get("control_id")},
                        )
                    if _stay_after_delivery(args, control_command=control.get("command")):
                        continue
                    return 20

            resumable = transport.resumable_claim(identity)
            held_claim = False
            if resumable is not None:
                task, claimed_path = resumable
                held_claim = True
                if _background(args) and notified_task_id == task.get("task_id"):
                    transport.write_heartbeat(identity, "running", task["task_id"])
                else:
                    rc = deliver_task(
                        root,
                        transport,
                        identity,
                        identity_path,
                        task,
                        claimed_path,
                        invocation,
                        recovered_claim=True,
                    )
                    if rc != 0 or not _stay_after_delivery(args):
                        return rc
                    notified_task_id = task.get("task_id")

            if not held_claim:
                transport.write_heartbeat(
                    identity, "watching" if slot["state"] == "on" else slot["state"], None
                )
                if slot["state"] == "on":
                    wait_s = args.interval
                    claimed = transport.claim_task(identity, args.lease_seconds)
                    if claimed is not None:
                        task, claimed_path = claimed
                        rc = deliver_task(
                            root,
                            transport,
                            identity,
                            identity_path,
                            task,
                            claimed_path,
                            invocation,
                            recovered_claim=False,
                        )
                        if rc != 0 or not _stay_after_delivery(args):
                            return rc
                        notified_task_id = task.get("task_id")
            if (not held_claim) and slot["state"] != "on" and args.state_wait_backoff_max:
                # Bounded backoff while the slot is not `on`: doubles per poll up
                # to the cap, resets as soon as the state returns to `on`.
                wait_s = min(wait_s * 2, args.state_wait_backoff_max)
            consecutive_errors = 0
        except Exception as error:
            # A transient fault in one poll (a momentary sharing violation, a
            # file that vanished mid-read) must not crash the whole slice with an
            # uncatchable traceback the agent's loop cannot dispatch on. Retry
            # the next poll within this slice; only a run of consecutive failures
            # is treated as a fatal adp_error.
            consecutive_errors += 1
            audit.record(
                root,
                "adp",
                {"event": "adp_error", "error": str(error), "consecutive": consecutive_errors},
            )
            if consecutive_errors >= 3:
                emit(
                    {
                        "event": "adp_error",
                        "error": str(error),
                        "identity_file": str(identity_path),
                        "action": "stop",
                    }
                )
                return 30
            wait_s = args.interval

        if _background(args) and time.monotonic() >= next_report:
            pending = None
            if notified_task_id:
                pending = notified_task_id
            else:
                held = transport.resumable_claim(identity)
                if held is not None:
                    pending = held[0].get("task_id")
            emit(
                {
                    "event": "watcher_report",
                    "lwar_id": identity["lwar_id"],
                    "identity_file": str(identity_path),
                    "state": slot["state"],
                    "pending_task_id": pending,
                    "uptime_s": round(time.monotonic() - started, 3),
                    "period_s": report_every,
                    "invocation_id": invocation["invocation_id"],
                    "invocation_epoch": invocation["epoch"],
                    "action": "acknowledge_keep_background",
                }
            )
            next_report = time.monotonic() + report_every

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            continue
        # Clamp the sleep to the slice deadline so a large --interval can never
        # overshoot the intended --timeout and starve control messages.
        time.sleep(min(wait_s if slot["state"] != "on" else args.interval, remaining))

    with transport.invocation_delivery_guard(identity, invocation) as current:
        if not current:
            emit(
                {
                    "event": "invocation_superseded",
                    "lwar_id": identity["lwar_id"],
                    "identity_file": str(identity_path),
                    "invocation_id": invocation["invocation_id"],
                    "invocation_epoch": invocation["epoch"],
                    "action": "stop_this_invocation",
                }
            )
            return 40
        transport.write_heartbeat(identity, "idle" if slot["state"] == "on" else slot["state"], None)
        emit(
            {
                "event": "idle_timeout" if slot["state"] == "on" else "state_wait",
                "lwar_id": identity["lwar_id"],
                "identity_file": str(identity_path),
                "state": slot["state"],
                "waited_s": args.timeout,
                "invocation_id": invocation["invocation_id"],
                "invocation_epoch": invocation["epoch"],
                "action": "watch_again",
            }
        )
        return 10


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="adp-watch", description="ADP mailbox watcher")
    parser.add_argument("--identity-file", required=True)
    parser.add_argument("--root", default=None)
    parser.add_argument("--interval", type=float, default=5.0)
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument("--lease-seconds", type=int, default=180)
    parser.add_argument(
        "--resident",
        action="store_true",
        help=(
            "Kimi official / blocking: stay across idle slices, print one JSON "
            "event, then exit (first task/control/fatal, or --max-runtime-s). "
            "Host reads stdout and restarts after complete."
        ),
    )
    parser.add_argument(
        "--background",
        action="store_true",
        help=(
            "host-supervised daemon: keep polling and heartbeats; print one JSON "
            "line only for task/control/fatal events or the --report-every pulse. "
            "Do not exit after a delivered task. Exit only on shutdown/retire/adp_error."
        ),
    )
    parser.add_argument(
        "--report-every",
        type=float,
        default=86400.0,
        help="background-only: emit watcher_report this often in seconds (default 86400 = 24h)",
    )
    parser.add_argument(
        "--state-wait-backoff-max",
        type=float,
        default=None,
        help="cap for the doubling poll interval while the slot is not on (default: no backoff)",
    )
    parser.add_argument(
        "--detach",
        action="store_true",
        help="spawn a detached --background watcher and return (host 1h limit bypass)",
    )
    parser.add_argument(
        "--stop",
        action="store_true",
        help="stop the detached watcher recorded for this identity",
    )
    parser.add_argument(
        "--max-runtime-s",
        type=float,
        default=None,
        help="exit with idle_timeout after this many idle seconds (Kimi: 3000 = 50m)",
    )
    return parser


def command_stop(args: argparse.Namespace) -> int:
    from .detach import stop_record, watcher_pid_path

    identity_path = Path(args.identity_file).resolve()
    identity = load_json(identity_path)
    root = resolve_identity_root(identity, identity_path, args.root)
    payload = stop_record(watcher_pid_path(root, identity["lwar_id"]))
    emit(payload)
    return 0 if payload.get("action") != "kill_failed" else 2


def command_detach(args: argparse.Namespace) -> int:
    from .detach import (
        child_argv_without_detach,
        event_log_path,
        spawn_detached,
        stop_record,
        watcher_pid_path,
        write_pid_record,
    )

    identity_path = Path(args.identity_file).resolve()
    identity = load_json(identity_path)
    root = resolve_identity_root(identity, identity_path, args.root)
    lwar_id = identity["lwar_id"]
    stop_record(watcher_pid_path(root, lwar_id))
    events = event_log_path(root, lwar_id)
    argv = [sys.executable, *child_argv_without_detach()]
    # scripts/adp_watch.py is sys.argv[0] when launched via wrapper
    pid = spawn_detached(argv, event_file=events)
    write_pid_record(
        watcher_pid_path(root, lwar_id),
        {
            "pid": pid,
            "lwar_id": lwar_id,
            "identity_file": str(identity_path),
            "event_file": str(events),
            "started_at": utc_now(),
            "detached": True,
        },
    )
    emit(
        {
            "event": "watcher_detached",
            "pid": pid,
            "lwar_id": lwar_id,
            "identity_file": str(identity_path),
            "event_file": str(events),
            "action": "host_may_exit",
        }
    )
    return 0


def main() -> int:
    args = build_parser().parse_args()
    if args.stop:
        return command_stop(args)
    if args.detach:
        if not args.background:
            raise SystemExit("--detach requires --background")
        return command_detach(args)
    validate_watch_args(args)
    return watch(args)


if __name__ == "__main__":
    raise SystemExit(main())
