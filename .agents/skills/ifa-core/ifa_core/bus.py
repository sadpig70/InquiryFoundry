"""Publish-and-collect over the PAO bus, for ifa roles.

Decision A12: this is an adapted copy of if_core.bus's loop, not an import.
if_core.make_pao_task binds the IF role enum and the if-lwar dispatcher into
every task it builds, so reusing it would mean modifying if-core — the one
thing this project must not do. The price is a second copy of the collect
loop; anyone changing the bus contract must look at both. The hard-won parts
carried over verbatim in spirit:

- match results by task_id in the BODY, not by worker — a stale outgoing/
  result once satisfied a wait for work that had not been done (live10g);
- read status from the nested ResultContract, not the envelope.

Tasks are namespaced task-ifa-… (A7) so the two pipelines' work is never
confusable on a shared mailbox.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

from .store import atomic_write_yaml

TIMEOUTS = {"predict": 900, "rebut": 900, "adjudicate": 600, "review": 1200}


def _skills_root() -> Path:
    return Path(__file__).resolve().parents[2]


def oa_script() -> Path:
    return _skills_root() / "pao-oa" / "scripts" / "oa.py"


def _oa(argv: list[str]) -> dict:
    proc = subprocess.run(
        [sys.executable, str(oa_script()), *argv],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    out = (proc.stdout or "").strip()
    try:
        return json.loads(out.splitlines()[-1]) if out else {}
    except (json.JSONDecodeError, IndexError):
        return {}


def task_id_for(run_id: str, role: str, lwar_id: str) -> str:
    return f"task-ifa-{run_id}-{role}-{lwar_id}-r0"


def ensure_jail(run_dir: Path, lwar_id: str) -> Path:
    j = run_dir / "jail" / lwar_id
    for sub in ("inbox", "outbox"):
        (j / sub).mkdir(parents=True, exist_ok=True)
    return j


def make_task(run_id: str, role: str, lwar_id: str, jail: Path) -> dict:
    if role not in TIMEOUTS:
        raise ValueError(role)
    inbox = jail / "inbox" / f"{role}.yaml"
    outbox = jail / "outbox" / f"{role}.yaml"
    return {
        "task_id": task_id_for(run_id, role, lwar_id),
        "role": role,
        "goal": f"ifa {role} for {run_id}",
        "instructions": (
            f"cwd is the jail. Read inbox/{role}.yaml ONLY - it contains the full "
            f"role contract and every input. Write outbox/{role}.yaml as a YAML "
            f"list exactly as the contract specifies. Do not open any other path."
        ),
        "cwd": str(jail),
        "input_files": [str(inbox)],
        "expected_output": str(outbox),
        "timeout_s": TIMEOUTS[role],
        "max_retries": 1,
        "attempt": 1,
        "permissions": {
            "read": [str(jail / "inbox")],
            "write": [str(jail / "outbox")],
            "network": False,
        },
        "completion_criteria": [
            "expected_output file exists",
            f"outbox/{role}.yaml is a non-empty YAML list",
        ],
        "workflow_id": f"workflow-ifa-{run_id}",
    }


def publish_collect(run_dir: Path, role: str, items: list, *,
                    poll_s: float = 15.0, runner=None) -> tuple[dict, list[str]]:
    """items: [(lwar_id, inbox_doc)]. Returns ({lwar: outbox_doc}, statuses)."""
    run_oa = runner or _oa
    run_dir = Path(run_dir)
    run_id = run_dir.name
    drafts = run_dir / "pao_drafts"
    drafts.mkdir(parents=True, exist_ok=True)
    pending: dict[str, str] = {}
    statuses: list[str] = []
    for lwar_id, inbox_doc in items:
        jail = ensure_jail(run_dir, lwar_id)
        atomic_write_yaml(jail / "inbox" / f"{role}.yaml", inbox_doc)
        task = make_task(run_id, role, lwar_id, jail)
        draft = drafts / f"{role}-{lwar_id}.json"
        draft.write_text(json.dumps(task, indent=2), encoding="utf-8")
        run_oa(["send", "--lwar-id", lwar_id, "--task-file", str(draft)])
        pending[lwar_id] = task["task_id"]
    deadline = time.monotonic() + TIMEOUTS[role]
    while pending and time.monotonic() < deadline:
        col = run_oa(["collect"])
        for res in col.get("results") or []:
            lid = res.get("lwar_id")
            if lid not in pending:
                continue
            body = res.get("result") or {}
            body_id = body.get("task_id") or res.get("task_id")
            if body_id and body_id != pending[lid]:
                continue  # stale outgoing/ leftovers must not satisfy the wait
            status = body.get("status") or res.get("status") or ""
            if status in ("succeeded", "failed", "cancelled"):
                statuses.append(status)
                del pending[lid]
        if pending:
            time.sleep(poll_s)
    for lid in pending:
        statuses.append("timed_out")
    outboxes = {}
    for lwar_id, _ in items:
        p = run_dir / "jail" / lwar_id / "outbox" / f"{role}.yaml"
        if p.is_file():
            from .store import load_yaml
            outboxes[lwar_id] = load_yaml(p)
    return outboxes, statuses
