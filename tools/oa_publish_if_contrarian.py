"""OA: materialize contrarian inboxes and publish EXPLOIT tasks."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"D:\InquiryFoundry")
OA = ROOT / ".agents" / "skills" / "pao-oa" / "scripts" / "oa.py"
CORE = ROOT / ".agents" / "skills" / "if-core"
sys.path.insert(0, str(CORE))

from if_core.bus import ensure_jail, make_pao_task
from if_core.compose import stamp_lineage
from if_core.cycle import cross_assign
from if_core.store import atomic_write_yaml, load_yaml

os.environ["PAO_OA_ID"] = os.environ.get("PAO_OA_ID", "oa-d2cf906650c14ee19364868369bcf574")

RUN_ID = "RUN-20260814-live1"
WF = "workflow-if-run-20260814-live1"
run_dir = ROOT / ".if" / "runs" / RUN_ID
brief = load_yaml(run_dir / "brief.yaml")

LWARS = [
    {"lwar_id": "LWAR1", "vendor_family": "anthropic"},
    {"lwar_id": "LWAR2", "vendor_family": "openai"},
    {"lwar_id": "LWAR3", "vendor_family": "moonshot"},
]

seeds = []
for lid in ("LWAR1", "LWAR2", "LWAR3"):
    box = load_yaml(run_dir / "jail" / lid / "outbox" / "generate.yaml") or []
    for s in box:
        seeds.append(stamp_lineage(s, lid, RUN_ID))

if len(seeds) != 9:
    print(f"SEED_COUNT {len(seeds)} expected 9", flush=True)
    sys.exit(2)

c_forb = {s["local_id"]: {s["lineage"]["generated_by"]} for s in seeds}
assign = cross_assign(seeds, LWARS, c_forb)

# persist assignment for later judge / compose
atomic_write_yaml(run_dir / "contrarian_assign.yaml", {
    lid: [q["local_id"] for q in qs] for lid, qs in assign.items()
})

nonce_path = run_dir / "run_nonce"
if not nonce_path.exists():
    nonce_path.write_bytes(os.urandom(32))

drafts_dir = run_dir / "pao_drafts"
drafts_dir.mkdir(exist_ok=True)

for lid, qs in assign.items():
    gens = {q["lineage"]["generated_by"] for q in qs}
    if lid in gens:
        print(f"SELF_EXAMINE {lid} gens={gens}", flush=True)
        sys.exit(3)
    jail = ensure_jail(run_dir, lid)
    inbox = {
        "schema": "if.task.v1",
        "role": "contrarian",
        "run_id": RUN_ID,
        "domain": brief["domain"],
        "lwar_id": lid,
        "phase": "EXPLOIT",
        "forbidden_premises": brief.get("forbidden_premises") or [],
        "questions": qs,
    }
    inbox_rel = Path("inbox") / "contrarian.yaml"
    outbox_rel = Path("outbox") / "contrarian.yaml"
    atomic_write_yaml(jail / inbox_rel, inbox)
    task = make_pao_task(
        RUN_ID, "contrarian", lid, jail,
        str(inbox_rel).replace("\\", "/"),
        str(outbox_rel).replace("\\", "/"),
        round_n=0,
    )
    task["workflow_id"] = WF
    task["timeout_s"] = 600
    task["max_retries"] = 1
    task["priority"] = 5
    task["depends_on"] = [
        "task-if-RUN-20260814-live1-generate-LWAR1-r0",
        "task-if-RUN-20260814-live1-generate-LWAR2-r1",
        "task-if-RUN-20260814-live1-generate-LWAR3-r0",
    ]
    task["cwd"] = str(jail)
    task["permissions"] = {
        "read": [str(jail / "inbox")],
        "write": [str(jail / "outbox")],
        "network": False,
    }
    task["instructions"] = (
        "You are an IF contrarian LWAR. Independent First. No self-examine.\n"
        "1. Run lwar.py begin with claim_token/execution_id/invocation_id from task_received BEFORE any other side effect.\n"
        "2. Do not read allocation.yaml, graph/, memory/, other jails, generate outboxes, or hints/.\n"
        "3. Read inbox/contrarian.yaml only.\n"
        "4. Execute: python D:\\InquiryFoundry\\.agents\\skills\\if-lwar\\scripts\\if_lwar.py "
        f"--role contrarian --lwar-id {lid} --jail {jail} "
        f"--inbox {jail / inbox_rel} --outbox {jail / outbox_rel}\n"
        "5. Verify outbox/contrarian.yaml is a YAML list. Each item: local_id, examiner, "
        "attacks (exactly 6: evidence/logic/premise/alternative/stakeholder/execution), "
        "kill_count, verdict SURVIVED|KILLED. No question_id. examiner must be this LWAR. "
        "kill only from evidence/premise rules (D19: kills>=1 => KILLED).\n"
        "6. complete with --result-file only (never --artifacts). artifacts: [\"outbox/contrarian.yaml\"]. "
        "status=succeeded only if step 5 verified.\n"
        "If you cannot satisfy criteria, submit blocked or failed — never optimistic succeeded."
    )
    task["completion_criteria"] = [
        "file exists: outbox/contrarian.yaml",
        "outbox/contrarian.yaml is a YAML list",
        "every item has local_id, examiner, attacks(len=6), kill_count, verdict SURVIVED|KILLED",
        "no item has a question_id",
        f"every examiner equals {lid}",
    ]
    draft = drafts_dir / f"contrarian-{lid}.json"
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
    print(
        f"ASSIGN {lid}: " + ",".join(q["local_id"] for q in qs),
        flush=True,
    )

print("PUBLISHED contrarian to", ",".join(sorted(assign)), flush=True)
