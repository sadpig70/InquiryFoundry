"""OA: create IF live run and publish generate tasks to active LWARs."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"D:\InquiryFoundry")
OA = ROOT / ".agents" / "skills" / "pao-oa" / "scripts" / "oa.py"
CORE = ROOT / ".agents" / "skills" / "if-core"
sys.path.insert(0, str(CORE))

from if_core.allocate import build_allocation
from if_core.bus import ensure_jail, make_pao_task
from if_core.store import Store, atomic_write_yaml
from if_core.paths import ensure_if_root

os.environ["PAO_OA_ID"] = os.environ.get("PAO_OA_ID", "oa-d2cf906650c14ee19364868369bcf574")

IF_ROOT = ROOT / ".if"
ensure_if_root(IF_ROOT)
store = Store(IF_ROOT)

BRIEF = {
    "brief_id": "RUN-20260814-live1",
    "mode": "normal",
    "domain": "scaling",
    "goal": "discovery",
    "constraints": [],
    "forbidden_premises": [],
    "must_consider_slices": {},
    "success_criteria": "live generate round",
    "evidence_hints": {
        "papers": ["papers/kaplan2020", "papers/hoffmann2022"],
    },
    "budget": {"max_rounds": 1, "max_seeds_per_lwar": 4},
}

LWARS = [
    {"lwar_id": "LWAR1", "vendor_family": "anthropic"},
    {"lwar_id": "LWAR2", "vendor_family": "openai"},
    {"lwar_id": "LWAR3", "vendor_family": "moonshot"},
]

PACK = ROOT / "tests" / "if" / "fixtures" / "papers.txt"
run_dir = IF_ROOT / "runs" / BRIEF["brief_id"]
if run_dir.exists():
    print(f"run exists {run_dir}", flush=True)
else:
    run_dir.mkdir(parents=True)

alloc = build_allocation(BRIEF, LWARS)
atomic_write_yaml(run_dir / "allocation.yaml", alloc)
atomic_write_yaml(run_dir / "brief.yaml", BRIEF)

drafts_dir = run_dir / "pao_drafts"
drafts_dir.mkdir(exist_ok=True)

for lid, sl in alloc.items():
    jail = ensure_jail(run_dir, lid)
    hints = jail / "hints"
    shutil.copy(PACK, hints / "papers.txt")
    inbox = {
        "schema": "if.task.v1",
        "role": "generate",
        "run_id": BRIEF["brief_id"],
        "domain": BRIEF["domain"],
        "lwar_id": lid,
        "phase": "EXPLORE",
        "allocation_slice": sl,
    }
    inbox_rel = Path("inbox") / "generate.yaml"
    outbox_rel = Path("outbox") / "generate.yaml"
    atomic_write_yaml(jail / inbox_rel, inbox)
    task = make_pao_task(
        BRIEF["brief_id"], "generate", lid, jail,
        str(inbox_rel).replace("\\", "/"),
        str(outbox_rel).replace("\\", "/"),
        round_n=0,
    )
    task["workflow_id"] = "workflow-if-run-20260814-live1"
    task["timeout_s"] = 900
    task["max_retries"] = 2
    task["priority"] = 5
    task["cwd"] = str(jail)
    task["permissions"] = {
        "read": [str(jail)],
        "write": [str(jail / "outbox")],
        "network": False,
    }
    task["instructions"] = (
        "You are an IF generate LWAR. Independent First.\n"
        "1. Run lwar.py begin with claim_token/execution_id/invocation_id from task_received BEFORE any other side effect.\n"
        "2. Do not read allocation.yaml, graph/, memory/, other jails, or other outboxes.\n"
        "3. Read inbox/generate.yaml and hints/ only.\n"
        "4. Execute: python D:\\InquiryFoundry\\.agents\\skills\\if-lwar\\scripts\\if_lwar.py "
        f"--role generate --lwar-id {lid} --jail {jail} "
        f"--inbox {jail / inbox_rel} --outbox {jail / outbox_rel}\n"
        "5. Verify outbox/generate.yaml exists and is a YAML list. Each seed must have local_id, "
        "operator, unknown_ref, evidence (>=1), and question_id must be null/absent.\n"
        "6. complete with --result-file only (never --artifacts). artifacts: [\"outbox/generate.yaml\"] "
        "as path strings. status=succeeded only if step 5 verified.\n"
        "If you cannot satisfy criteria, submit blocked or failed — never optimistic succeeded."
    )
    task["completion_criteria"] = [
        "file exists: outbox/generate.yaml",
        "outbox/generate.yaml is a YAML list",
        "every item has local_id, operator, unknown_ref, evidence with at least one source",
        "no item has a non-null question_id",
    ]
    draft = drafts_dir / f"generate-{lid}.json"
    draft.write_text(json.dumps(task, indent=2), encoding="utf-8")
    p = subprocess.run(
        [sys.executable, str(OA), "send", "--lwar-id", lid, "--task-file", str(draft)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    print(p.stdout.strip() or p.stderr.strip(), flush=True)
    if p.returncode != 0:
        print(f"SEND_FAIL {lid} rc={p.returncode}", flush=True)
        sys.exit(p.returncode)

print("PUBLISHED generate to", ",".join(alloc), flush=True)
