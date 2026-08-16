"""Detach a watcher from the host process tree and stop it by PID file."""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from .common import mailbox_root, utc_now


def watcher_pid_path(root: Path, lwar_id: str) -> Path:
    return mailbox_root(root, lwar_id) / "watcher.pid.json"


def pending_pid_path(root: Path, request_id: str) -> Path:
    return root / "var" / "identities" / f"{request_id}.watcher.pid.json"


def event_log_path(root: Path, key: str) -> Path:
    return root / "var" / "adp" / f"{key}.events.jsonl"


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    except SystemError:
        return False
    return True


def write_pid_record(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def read_pid_record(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def stop_pid(pid: int) -> str:
    if not pid_alive(pid):
        return "already_dead"
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            text=True,
            check=False,
        )
    else:
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            return "already_dead"
        for _ in range(20):
            if not pid_alive(pid):
                return "terminated"
            time.sleep(0.1)
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            return "terminated"
    return "killed" if not pid_alive(pid) else "kill_failed"


def stop_record(path: Path) -> dict[str, Any]:
    rec = read_pid_record(path)
    if rec is None:
        return {"event": "watcher_stop", "action": "no_pid_file", "pid_file": str(path)}
    pid = int(rec.get("pid") or 0)
    action = stop_pid(pid)
    if action != "kill_failed":
        path.unlink(missing_ok=True)
    return {
        "event": "watcher_stop",
        "action": action,
        "pid": pid,
        "pid_file": str(path),
        "identity_file": rec.get("identity_file"),
    }


def spawn_detached(argv: list[str], *, event_file: Path | None = None) -> int:
    env = os.environ.copy()
    env["PAO_ADP_DETACHED"] = "1"
    if event_file is not None:
        event_file.parent.mkdir(parents=True, exist_ok=True)
        env["PAO_ADP_EVENT_FILE"] = str(event_file)
    kwargs: dict[str, Any] = {
        "args": argv,
        "env": env,
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "close_fds": True,
    }
    if sys.platform == "win32":
        flags = subprocess.CREATE_NEW_PROCESS_GROUP | getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
        flags |= 0x08000000  # CREATE_NO_WINDOW
        kwargs["creationflags"] = flags
    else:
        kwargs["start_new_session"] = True
    proc = subprocess.Popen(**kwargs)
    return int(proc.pid)


def child_argv_without_detach(argv: list[str] | None = None) -> list[str]:
    src = list(argv if argv is not None else sys.argv)
    return [a for a in src if a != "--detach"]


DEFAULT_WAIT_EVENTS = frozenset(
    {"task_received", "control", "adp_error", "identity_adopted", "watcher_detached"}
)


def _read_offset(path: Path) -> int:
    if not path.is_file():
        return 0
    try:
        return max(0, int(path.read_text(encoding="utf-8").strip() or "0"))
    except ValueError:
        return 0


def wait_event_line(
    event_file: Path,
    *,
    timeout_s: float,
    offset_file: Path | None = None,
    interesting: frozenset[str] = DEFAULT_WAIT_EVENTS,
    poll_s: float = 1.0,
) -> dict[str, Any]:
    """Block until a new interesting JSONL event appears. One call, no agent loop."""
    marker = offset_file or Path(str(event_file) + ".offset")
    deadline = time.monotonic() + timeout_s
    offset = _read_offset(marker)
    event_file.parent.mkdir(parents=True, exist_ok=True)
    event_file.touch(exist_ok=True)
    if offset == 0:
        offset = event_file.stat().st_size
        marker.write_text(str(offset), encoding="utf-8")
    while time.monotonic() < deadline:
        try:
            size = event_file.stat().st_size
        except OSError:
            size = 0
        if size < offset:
            offset = 0
        if size > offset:
            with event_file.open("r", encoding="utf-8") as handle:
                handle.seek(offset)
                chunk = handle.read()
                offset = handle.tell()
            marker.write_text(str(offset), encoding="utf-8")
            for raw in chunk.splitlines():
                line = raw.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(payload, dict):
                    continue
                if payload.get("event") in interesting:
                    return payload
        time.sleep(min(poll_s, max(0.05, deadline - time.monotonic())))
    return {
        "event": "idle_timeout",
        "waited_s": timeout_s,
        "event_file": str(event_file),
        "action": "wait_again_or_stop",
    }
