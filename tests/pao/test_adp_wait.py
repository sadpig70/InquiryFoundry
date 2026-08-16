from __future__ import annotations

import json
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".agents" / "skills" / "pao-lwar"))

from pao_runtime.detach import wait_event_line  # noqa: E402


def test_wait_event_returns_new_task_line(tmp_path):
    log = tmp_path / "e.jsonl"
    log.write_text("", encoding="utf-8")
    offset = tmp_path / "e.off"

    def writer() -> None:
        time.sleep(0.2)
        with log.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"event": "task_received", "task_id": "task-x"}) + "\n")

    threading.Thread(target=writer, daemon=True).start()
    got = wait_event_line(log, timeout_s=3.0, offset_file=offset, poll_s=0.05)
    assert got["event"] == "task_received"
    assert got["task_id"] == "task-x"


def test_wait_event_timeout(tmp_path):
    log = tmp_path / "empty.jsonl"
    log.write_text("", encoding="utf-8")
    got = wait_event_line(log, timeout_s=0.25, offset_file=tmp_path / "o", poll_s=0.05)
    assert got["event"] == "idle_timeout"
