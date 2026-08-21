from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

from .const import DEFAULT_MAX_RETRIES, OMIT_STATUS, PHASES, ROLES
from .store import atomic_write_yaml, load_yaml


def phase_of(role: str) -> str:
    return PHASES[role]


def propose_task_id(run_id: str, role: str, lwar_id: str, round_n: int = 0) -> str:
    return f"task-if-{run_id}-{role}-{lwar_id}-r{round_n}"


def parse_round_n(task_id: str) -> int:
    if "-r" not in task_id:
        return 0
    tail = task_id.rsplit("-r", 1)[-1]
    return int(tail) if tail.isdigit() else 0


def outbox_rel(role: str, round_n: int = 0) -> str:
    return f"outbox/{role}-r{round_n}.yaml"


def inbox_rel(role: str, round_n: int = 0) -> str:
    return f"inbox/{role}-r{round_n}.yaml"


def load_role_outbox(jail: Path, role: str, round_n: int = 0):
    path = jail / "outbox" / f"{role}-r{round_n}.yaml"
    if path.is_file():
        return load_yaml(path) or []
    legacy = jail / "outbox" / f"{role}.yaml"
    if legacy.is_file():
        return load_yaml(legacy) or []
    return []


def jail_dir(run_dir: Path, lwar_id: str) -> Path:
    return run_dir / "jail" / lwar_id


def ensure_jail(run_dir: Path, lwar_id: str) -> Path:
    j = jail_dir(run_dir, lwar_id)
    for sub in ("inbox", "hints", "outbox"):
        (j / sub).mkdir(parents=True, exist_ok=True)
    return j


def path_allowed(patterns: list[str], lwar_id: str, opened_path: str) -> bool:
    opened = Path(opened_path).resolve()
    opened_s = str(opened).replace("\\", "/")
    for raw in patterns:
        pat = raw.replace("{own_lwar}", lwar_id).replace("\\", "/")
        if pat.endswith("/**"):
            prefix = pat[:-3]
            if prefix in opened_s or opened_s.endswith(prefix.split("/")[-1]):
                # prefix match on normalized parts
                if _has_prefix(opened_s, prefix):
                    return True
        elif opened_s.endswith(pat) or pat in opened_s:
            return True
    return False


def _has_prefix(opened: str, prefix: str) -> bool:
    # match .../jail/LWAR1/inbox or hints
    parts = prefix.strip("/").split("/")
    return all(p in opened for p in parts if p and p != "*")


FORBIDDEN_ANY = ("allocation.yaml", "/graph/", "/memory/", "/runs/")


def assert_visible(lwar_id: str, role: str, opened_path: str, jail: Path) -> None:
    opened = Path(opened_path).resolve()
    opened_s = str(opened).replace("\\", "/")
    if any(tok in opened_s for tok in ("allocation.yaml", "/graph/", "/memory/")):
        raise PermissionError("visibility jail")
    jail_s = str(jail.resolve()).replace("\\", "/")
    if not opened_s.startswith(jail_s):
        raise PermissionError("visibility jail")
    if role == "generate":
        ok = "/inbox/" in opened_s or "/hints/" in opened_s
    else:
        ok = "/inbox/" in opened_s
    if not ok:
        raise PermissionError("visibility jail")


def trusted_code_roots() -> list[str]:
    skills = _skills_root()
    return [str(skills / "if-lwar"), str(skills / "if-core")]


def make_pao_task(run_id: str, role: str, lwar: str, jail: Path,
                  inbox_rel_s: str, outbox_rel_s: str, round_n: int = 0,
                  *, stub: bool = False, parent_task_id: str | None = None) -> dict:
    if role not in ROLES:
        raise ValueError(role)
    data_read = [str(jail)] if role == "generate" else [str(jail / "inbox")]
    # A reviewer reads the whole run at once, so it gets the longest slice.
    timeout = {"generate": 900, "contrarian": 900, "judge": 600, "review": 1200}[role]
    dispatcher = _skills_root() / "if-lwar" / "scripts" / "if_lwar.py"
    if stub:
        run_line = (
            f"python {dispatcher} --stub --role {role} --lwar-id {lwar} "
            f"--jail {jail} --inbox {jail / inbox_rel_s} --outbox {jail / outbox_rel_s}"
        )
    else:
        run_line = (
            f"Write outbox via role SKILL (AI_). Then: python {dispatcher} --validate-only "
            f"--role {role} --lwar-id {lwar} --jail {jail} "
            f"--inbox {jail / inbox_rel_s} --outbox {jail / outbox_rel_s}"
        )
    attempt = round_n + 1
    task = {
        "task_id": propose_task_id(run_id, role, lwar, round_n),
        "role": role,
        "goal": f"IF {role} for {run_id}",
        "instructions": (
            f"cwd is jail. Read {inbox_rel_s} only (plus trusted IF skill code). "
            f"Write {outbox_rel_s}. {run_line}"
        ),
        "cwd": str(jail),
        "input_files": [str(jail / inbox_rel_s)],
        "expected_output": str(jail / outbox_rel_s),
        "timeout_s": timeout,
        "max_retries": DEFAULT_MAX_RETRIES,
        "attempt": attempt,
        "permissions": {
            "read": data_read + trusted_code_roots(),
            "write": [str(jail / "outbox")],
            "network": False,
        },
        "completion_criteria": [
            "expected_output file exists",
            "expected_output validates against if outbox schema for task.role",
            "outbox list is non-empty",
            "no deterministic stub markers unless adapter_options.if_stub",
        ],
        "adapter_options": {
            "if_run_id": run_id,
            "if_phase": phase_of(role),
            "if_schema": "if.task.v1",
            "if_stub": stub,
            "if_round": round_n,
        },
    }
    if parent_task_id:
        task["parent_task_id"] = parent_task_id
        task["adapter_options"]["retry_of"] = parent_task_id
    return task


def _oa(args: list[str]) -> dict:
    script = oa_script()
    p = subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True,
        text=True,
    )
    raw = (p.stdout or "").strip()
    if p.returncode != 0:
        raise RuntimeError(raw or p.stderr or f"oa {' '.join(args)} rc={p.returncode}")
    return json.loads(raw) if raw.startswith("{") else {"raw": raw}


def publish_collect(run_dir: Path, role: str, items: list, timeout_s: int,
                    *, poll_s: float = 15.0, runner=None) -> tuple[dict, list[str]]:
    """Send role inboxes, poll collect until terminal or timeout. succeeded only."""
    run_oa = runner or (lambda argv: _oa(argv))
    run_dir = Path(run_dir)
    run_id = run_dir.name
    drafts = run_dir / "pao_drafts"
    drafts.mkdir(exist_ok=True)
    pending: dict[str, str] = {}
    observed: list[str] = []
    pending_round: dict[str, int] = {}
    for lwar_id, inbox in items:
        jail = ensure_jail(run_dir, lwar_id)
        parent = inbox.get("parent_task_id")
        round_n = int(inbox.get("round_n") or (parse_round_n(parent) + 1 if parent else 0))
        in_rel = inbox_rel(role, round_n)
        out_rel = outbox_rel(role, round_n)
        atomic_write_yaml(jail / in_rel, inbox)
        stub = bool(inbox.get("stub"))
        task = make_pao_task(
            run_id, role, lwar_id, jail, in_rel, out_rel, round_n,
            stub=stub, parent_task_id=parent,
        )
        task["workflow_id"] = f"workflow-if-{run_id}"
        draft = drafts / f"{role}-{lwar_id}-r{round_n}.json"
        draft.write_text(json.dumps(task, indent=2), encoding="utf-8")
        run_oa(["send", "--lwar-id", lwar_id, "--task-file", str(draft)])
        pending[lwar_id] = task["task_id"]
        pending_round[lwar_id] = round_n
    deadline = time.monotonic() + timeout_s
    recovered = False
    accepted: dict[str, list] = {}
    while pending and time.monotonic() < deadline:
        col = run_oa(["collect"])
        for res in col.get("results") or []:
            lid = res.get("lwar_id")
            if lid not in pending:
                continue
            # `oa collect` nests the ResultContract under "result"; the status
            # lives there, not on the envelope. Reading it off the envelope
            # yielded "" for every collected result, so nothing ever matched
            # `succeeded`, pending never drained, and healthy runs that had
            # already submitted were reported as timed_out.
            body = res.get("result") or {}
            st = (
                body.get("status")
                or res.get("status")
                or res.get("result_status")
                or ""
            )
            observed.append(st)
            if st in OMIT_STATUS or st == "failed":
                pending.pop(lid, None)
                continue
            if st == "succeeded":
                box = load_role_outbox(run_dir / "jail" / lid, role, pending_round.get(lid, 0))
                accepted[lid] = box
                pending.pop(lid, None)
        if not pending:
            break
        if not recovered and time.monotonic() + poll_s >= deadline:
            run_oa(["recover", "--delivery-timeout", str(int(timeout_s))])
            recovered = True
        time.sleep(poll_s)
    for lid in list(pending):
        observed.append("timed_out")
        pending.pop(lid)
    return accepted, observed


OA_CMDS = (
    "send", "collect", "recover", "status", "presence", "audit-health",
    "validate", "workflow-status", "control",
)


def cancelled_task_ids(pao_root: Path, lwar_id: str) -> list[str]:
    folder = Path(pao_root) / "mailbox" / lwar_id / "cancelled"
    if not folder.is_dir():
        return []
    return sorted(p.stem for p in folder.glob("*.json"))


def _skills_root() -> Path:
    """The directory holding the sibling skills (if-core, pao-oa, pao-lwar, ...).

    if_core/bus.py lives at <skills>/if-core/if_core/bus.py, so the skills root
    is parents[2]. It was parents[3] here, which resolved to `.agents` and put
    `.agents/pao-oa/scripts/oa.py` on the command line — a path that does not
    exist, so every --pao publish died on the first send. The two other places
    in this file that need the same root already used parents[2].
    """
    return Path(__file__).resolve().parents[2]


def oa_script() -> Path:
    return _skills_root() / "pao-oa" / "scripts" / "oa.py"


def lwar_script() -> Path:
    return _skills_root() / "pao-lwar" / "scripts" / "lwar.py"
