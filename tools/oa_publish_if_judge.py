"""OA: materialize blinded judge inboxes and publish EXPLOIT judge tasks."""
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
from if_core.cycle import cross_assign, mint_anon
from if_core.judge import blind_packet
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

dissents = {}
for lid in ("LWAR1", "LWAR2", "LWAR3"):
    recs = load_yaml(run_dir / "jail" / lid / "outbox" / "contrarian.yaml") or []
    for r in recs:
        if r.get("local_id"):
            dissents[r["local_id"]] = r

missing = [s["local_id"] for s in seeds if s["local_id"] not in dissents]
if missing:
    print("PROTOCOL_INCOMPLETE missing=" + ",".join(missing), flush=True)
    sys.exit(2)

nonce_path = run_dir / "run_nonce"
if not nonce_path.is_file():
    print("NO_RUN_NONCE", flush=True)
    sys.exit(2)
nonce = nonce_path.read_bytes()

j_forb = {s["local_id"]: {s["lineage"]["generated_by"]} for s in seeds}
for s in seeds:
    d = dissents[s["local_id"]]
    examiner = d.get("examiner")
    if examiner:
        j_forb[s["local_id"]].add(examiner)

assign = cross_assign(seeds, LWARS, j_forb)

anon_map = {}
assign_ids = {}
for lid, qs in assign.items():
    gens_ex = set()
    for q in qs:
        gens_ex |= j_forb[q["local_id"]]
    if lid in gens_ex:
        print(f"FORBIDDEN_JUDGE {lid} banned={sorted(gens_ex)}", flush=True)
        sys.exit(3)
    assign_ids[lid] = [q["local_id"] for q in qs]
    jail = ensure_jail(run_dir, lid)
    blinded = []
    excl = set()
    for q in qs:
        aid = mint_anon(nonce, q["local_id"])
        anon_map[aid] = q["local_id"]
        blinded.append(blind_packet(q, aid))
        excl |= j_forb[q["local_id"]]
    inbox = {
        "schema": "if.task.v1",
        "role": "judge",
        "run_id": RUN_ID,
        "lwar_id": lid,
        "phase": "EXPLOIT",
        "exclude_lwars": sorted(excl),
        "questions": blinded,
    }
    inbox_rel = Path("inbox") / "judge.yaml"
    outbox_rel = Path("outbox") / "judge.yaml"
    atomic_write_yaml(jail / inbox_rel, inbox)
    task = make_pao_task(
        RUN_ID, "judge", lid, jail,
        str(inbox_rel).replace("\\", "/"),
        str(outbox_rel).replace("\\", "/"),
        round_n=0,
    )
    task["workflow_id"] = WF
    task["timeout_s"] = 600
    task["max_retries"] = 1
    task["priority"] = 5
    task["depends_on"] = [
        "task-if-RUN-20260814-live1-contrarian-LWAR1-r0",
        "task-if-RUN-20260814-live1-contrarian-LWAR2-r0",
        "task-if-RUN-20260814-live1-contrarian-LWAR3-r1",
    ]
    task["cwd"] = str(jail)
    task["permissions"] = {
        "read": [str(jail / "inbox")],
        "write": [str(jail / "outbox")],
        "network": False,
    }
    task["instructions"] = (
        "You are an IF blind judge. No question_id, local_id, generated_by, novelty.\n"
        "1. Run lwar.py begin with claim_token/execution_id/invocation_id from task_received BEFORE any other side effect.\n"
        "2. Do not read allocation.yaml, graph/, memory/, other jails, generate/contrarian files, or hints/.\n"
        "3. Read inbox/judge.yaml only. Packets are already blinded (anon_id).\n"
        "4. Execute: python D:\\InquiryFoundry\\.agents\\skills\\if-lwar\\scripts\\if_lwar.py "
        f"--role judge --lwar-id {lid} --jail {jail} "
        f"--inbox {jail / inbox_rel} --outbox {jail / outbox_rel}\n"
        "5. Verify outbox/judge.yaml is a YAML list. Each item: anon_id, verdict SCORED|GATE_FAIL, "
        "scores, notes. Forbidden keys: question_id, local_id, generated_by, novelty, diversity_contribution. "
        "Scores subset of impact/testability/grounding/actionability.\n"
        "6. complete with --result-file only (never --artifacts). artifacts: [\"outbox/judge.yaml\"]. "
        "status=succeeded only if step 5 verified.\n"
        "If you cannot satisfy criteria, submit blocked or failed — never optimistic succeeded."
    )
    task["completion_criteria"] = [
        "file exists: outbox/judge.yaml",
        "outbox/judge.yaml is a YAML list",
        "every item has anon_id, verdict SCORED|GATE_FAIL, scores, notes",
        "no item has question_id, local_id, generated_by, novelty, or diversity_contribution",
    ]
    draft = run_dir / "pao_drafts" / f"judge-{lid}.json"
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
    print(f"ASSIGN {lid}: " + ",".join(assign_ids[lid]), flush=True)

atomic_write_yaml(run_dir / "judge_assign.yaml", assign_ids)
atomic_write_yaml(run_dir / "anon_map.yaml", anon_map)
print("PUBLISHED judge to", ",".join(sorted(assign)), flush=True)
