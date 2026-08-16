from __future__ import annotations

import hashlib
import hmac
from pathlib import Path

import pytest
import yaml

CORE = Path(__file__).resolve().parents[2] / ".agents" / "skills" / "if-core"
import sys

sys.path.insert(0, str(CORE))

from if_core.allocate import build_allocation, vendor_family
from if_core.bus import assert_visible, ensure_jail, make_pao_task, phase_of
from if_core.const import OPERATORS
from if_core.cycle import close_run, inquiry_cycle, mint_anon
from if_core.gates import mechanical_gates, source_in_hints
from if_core.schema import SchemaError, validate_obj
from if_core.state import TransitionError, assert_transition
from if_core.store import Blocked, Store

FIX = Path(__file__).parent / "fixtures"


def load(name: str):
    return yaml.safe_load((FIX / name).read_text(encoding="utf-8"))


def test_operators_unique_12():
    ids = [o[0] for o in OPERATORS]
    assert len(ids) == 12
    assert len(set(ids)) == 12


def test_v4_novelty_forbidden():
    q = load("valid_qo.yaml")
    q["scores"] = {"novelty": 0.9}
    with pytest.raises(SchemaError, match="novelty"):
        validate_obj("qo", q)


def test_valid_qo_passes():
    validate_obj("qo", load("valid_qo.yaml"))


def test_invalid_qo_fails():
    with pytest.raises(SchemaError):
        validate_obj("qo", load("invalid_qo.yaml"))


def test_v10_judge_qid_rejected():
    with pytest.raises(SchemaError, match="question_id"):
        validate_obj("score_card_outbox", load("judge_outbox_with_qid.yaml"))


def test_v16_contrarian_qid_rejected():
    with pytest.raises(SchemaError, match="question_id"):
        validate_obj("dissent_report_outbox", load("contrarian_with_qid.yaml"))


def test_v3_oa_cannot_adopt():
    with pytest.raises(TransitionError, match="ADOPTED"):
        assert_transition("REVIEWED", "ADOPTED", actor="oa", reviewer_ok=False)
    assert_transition("REVIEWED", "ADOPTED", actor="human", reviewer_ok=True)


def test_v9_worker_cannot_alloc(tmp_path):
    st = Store(tmp_path)
    with pytest.raises(PermissionError, match="V9"):
        st.alloc_question_id("RUN-20260814-1", actor="worker")
    qid = st.alloc_question_id("RUN-20260814-1", actor="cycle")
    assert qid.startswith("Q-20260814-")


def test_first_write_must_be_draft(tmp_path):
    st = Store(tmp_path)
    q = load("valid_qo.yaml")
    q["status"] = "SCORED"
    with pytest.raises(ValueError, match="DRAFT"):
        st.write_question(q, actor="oa")


def test_source_in_hints_min_len():
    assert not source_in_hints("arxiv.org/abs/1", ["ar"])
    assert source_in_hints("papers/kaplan2020", ["papers/kaplan2020"])


def test_no_gfalsify_name():
    g = mechanical_gates(load("valid_qo.yaml"), ["papers/kaplan2020", "papers/hoffmann2022"])
    assert "G-FALSIFY" not in g
    assert g["G-DUP"] == "human"


def test_v5_two_lwar_normal_blocked(tmp_path):
    brief = load("brief.yaml")
    brief["brief_id"] = "RUN-20260814-v5"
    lwars = [
        {"lwar_id": "LWAR1", "vendor_family": "anthropic"},
        {"lwar_id": "LWAR2", "vendor_family": "openai"},
    ]
    with pytest.raises(Blocked, match="3 LWARs"):
        inquiry_cycle(brief, lwars, tmp_path, { "papers": FIX / "papers.txt" })


def test_missing_vendor_family():
    with pytest.raises(Blocked, match="vendor_family"):
        vendor_family({"lwar_id": "LWAR1"})


def test_phase_of_and_task_id():
    assert phase_of("generate") == "EXPLORE"
    t = make_pao_task("RUN-1", "generate", "LWAR1", Path("/tmp/jail"), "inbox/a.yaml", "outbox/a.yaml")
    assert t["task_id"].startswith("task-if-")
    assert t["permissions"]["network"] is False
    assert t["max_retries"] == 2
    assert any("if-core" in p or p.endswith("if-core") for p in t["permissions"]["read"])
    assert "doctor" not in t


def test_v1_visibility(tmp_path):
    jail = ensure_jail(tmp_path / "runs" / "R", "LWAR1")
    inbox = jail / "inbox" / "t.yaml"
    inbox.write_text("x: 1", encoding="utf-8")
    assert_visible("LWAR1", "generate", str(inbox), jail)
    alloc = tmp_path / "runs" / "R" / "allocation.yaml"
    alloc.write_text("a: 1", encoding="utf-8")
    with pytest.raises(PermissionError):
        assert_visible("LWAR1", "generate", str(alloc), jail)


def test_v12_forged_lineage_dropped():
    from if_core.compose import stamp_lineage
    from if_core.store import Drop
    seed = {"local_id": "LWAR1-01", "lineage": {"generated_by": "LWAR9"}}
    with pytest.raises(Drop):
        stamp_lineage(seed, "LWAR1", "RUN-1")
    ok = stamp_lineage({"local_id": "x", "lineage": {"generated_by": "LWAR1"}}, "LWAR1", "RUN-1")
    assert ok["lineage"]["run_id"] == "RUN-1"


def test_v18_anon_not_unsalted():
    nonce = b"n" * 32
    aid = mint_anon(nonce, "LWAR1-01")
    unsalted = "A-" + hashlib.sha256(b"LWAR1-01").hexdigest()[:12]
    assert aid != unsalted
    assert aid == mint_anon(nonce, "LWAR1-01")


def test_e2e_fixture_and_close(tmp_path):
    brief = load("brief.yaml")
    brief["brief_id"] = "RUN-20260814-e2e"
    lwars = [
        {"lwar_id": "LWAR1", "vendor_family": "anthropic"},
        {"lwar_id": "LWAR2", "vendor_family": "openai"},
        {"lwar_id": "LWAR3", "vendor_family": "alibaba"},
    ]
    packs = {"papers": FIX / "papers.txt"}
    report = inquiry_cycle(brief, lwars, tmp_path, packs)
    assert report["seed_count"] > 0
    assert report["qo_count"] == report["seed_count"]
    assert report["human"] == "awaiting_human"
    assert report["protocol_valid"] is True or report["contributing_generate_lwars"] >= 1
    # fill review
    run_dir = tmp_path / "runs" / brief["brief_id"]
    review = yaml.safe_load((run_dir / "review.yaml").read_text(encoding="utf-8"))
    assert "scores" not in review
    assert "generated_by" not in review
    for d in review["decisions"]:
        if not d.get("informational"):
            d["decision"] = "defer"
            d["reason"] = "fixture defer"
    review["reviewer"] = "tester"
    (run_dir / "review.yaml").write_text(yaml.safe_dump(review, allow_unicode=True), encoding="utf-8")
    closed = close_run(tmp_path, brief["brief_id"])
    assert closed["status"] == "closed"


def test_v15_ablation_adopt_no_mutation(tmp_path):
    brief = load("brief.yaml")
    brief["brief_id"] = "RUN-20260814-abl"
    brief["mode"] = "ablation"
    lwars = [
        {"lwar_id": "LWAR1", "vendor_family": "anthropic"},
        {"lwar_id": "LWAR2", "vendor_family": "openai"},
        {"lwar_id": "LWAR3", "vendor_family": "alibaba"},
    ]
    report = inquiry_cycle(brief, lwars, tmp_path, {"papers": FIX / "papers.txt"})
    if report["seed_count"] == 0:
        pytest.skip("no seeds")
    run_dir = tmp_path / "runs" / brief["brief_id"]
    review = yaml.safe_load((run_dir / "review.yaml").read_text(encoding="utf-8"))
    for d in review["decisions"]:
        if not d.get("informational"):
            d["decision"] = "adopt"
            d["reason"] = "should fail"
    review["reviewer"] = "tester"
    (run_dir / "review.yaml").write_text(yaml.safe_dump(review, allow_unicode=True), encoding="utf-8")
    before = list((tmp_path / "graph" / "questions").glob("Q-*.yaml"))
    with pytest.raises(Blocked, match="ablation"):
        close_run(tmp_path, brief["brief_id"])
    after = list((tmp_path / "graph" / "questions").glob("Q-*.yaml"))
    assert len(after) == len(before)


def test_v11_reviewed_resume(tmp_path):
    brief = load("brief.yaml")
    brief["brief_id"] = "RUN-20260814-v11"
    lwars = [
        {"lwar_id": "LWAR1", "vendor_family": "anthropic"},
        {"lwar_id": "LWAR2", "vendor_family": "openai"},
        {"lwar_id": "LWAR3", "vendor_family": "alibaba"},
    ]
    report = inquiry_cycle(brief, lwars, tmp_path, {"papers": FIX / "papers.txt"})
    if report["scored_count"] == 0:
        pytest.skip("no scored")
    store = Store(tmp_path)
    scored = store.load_status("SCORED")
    q = scored[0]
    q["status"] = "REVIEWED"
    store.write_question(q, actor="human", reviewer_ok=True)
    run_dir = tmp_path / "runs" / brief["brief_id"]
    review = yaml.safe_load((run_dir / "review.yaml").read_text(encoding="utf-8"))
    for d in review["decisions"]:
        if d["question_id"] == q["question_id"]:
            d["decision"] = "defer"
            d["reason"] = "resume"
            d["informational"] = False
        elif not d.get("informational"):
            d["decision"] = "defer"
            d["reason"] = "other"
    review["reviewer"] = "tester"
    (run_dir / "review.yaml").write_text(yaml.safe_dump(review, allow_unicode=True), encoding="utf-8")
    close_run(tmp_path, brief["brief_id"])
    q2 = store.load_question(q["question_id"])
    assert q2["status"] == "DEFERRED"


def test_v7_empty_reviewer(tmp_path):
    brief = load("brief.yaml")
    brief["brief_id"] = "RUN-20260814-v7"
    lwars = [
        {"lwar_id": "LWAR1", "vendor_family": "anthropic"},
        {"lwar_id": "LWAR2", "vendor_family": "openai"},
        {"lwar_id": "LWAR3", "vendor_family": "alibaba"},
    ]
    report = inquiry_cycle(brief, lwars, tmp_path, {"papers": FIX / "papers.txt"})
    if report["seed_count"] == 0:
        pytest.skip("no seeds")
    with pytest.raises(Blocked, match="reviewer"):
        close_run(tmp_path, brief["brief_id"])


def test_v14_empty_unknowns(tmp_path):
    brief = load("brief.yaml")
    brief["brief_id"] = "RUN-20260814-empty"
    empty = tmp_path / "empty.txt"
    empty.write_text("All claims sourced. source: papers/onlyone\n", encoding="utf-8")
    brief["evidence_hints"] = {"papers": ["papers/onlyone"]}
    lwars = [
        {"lwar_id": "LWAR1", "vendor_family": "anthropic"},
        {"lwar_id": "LWAR2", "vendor_family": "openai"},
        {"lwar_id": "LWAR3", "vendor_family": "alibaba"},
    ]
    report = inquiry_cycle(brief, lwars, tmp_path, {"papers": empty})
    assert report["seed_count"] == 0
    assert report.get("reason") == "empty_unknowns_or_seeds"


def test_reuse_or_mint_idempotent(tmp_path):
    st = Store(tmp_path)
    run = tmp_path / "runs" / "RUN-20260814-1"
    run.mkdir(parents=True)
    a = st.reuse_or_mint(run, "LWAR1-01", "RUN-20260814-1")
    b = st.reuse_or_mint(run, "LWAR1-01", "RUN-20260814-1")
    assert a == b


def test_if_oa_has_no_runtime():
    oa = Path(__file__).resolve().parents[2] / ".agents" / "skills" / "if-oa"
    assert not (oa / "pao_runtime").exists()


def test_validate_cli():
    import subprocess
    exe = CORE / "scripts" / "validate.py"
    r = subprocess.run(
        ["python", str(exe), "--kind", "qo", str(FIX / "valid_qo.yaml")],
        capture_output=True, text=True,
    )
    assert r.returncode == 0
    r2 = subprocess.run(
        ["python", str(exe), "--kind", "qo", str(FIX / "invalid_qo.yaml")],
        capture_output=True, text=True,
    )
    assert r2.returncode == 1


def test_if_lwar_self_test():
    import subprocess
    script = Path(__file__).resolve().parents[2] / ".agents" / "skills" / "if-lwar" / "scripts" / "if_lwar.py"
    r = subprocess.run(["python", str(script), "--self-test"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr + r.stdout
    assert '"ok": true' in r.stdout.replace(" ", "") or '"ok":true' in r.stdout.replace(" ", "")


def test_semantic_rejects_empty_and_stub():
    from if_core.semantic import SemanticError, assert_role_output
    with pytest.raises(SemanticError, match="empty"):
        assert_role_output("generate", [], allow_stub=False)
    with pytest.raises(SemanticError, match="stub"):
        assert_role_output(
            "contrarian",
            [{"attacks": [{"attack": "deterministic stub", "rationale": "x"}] * 6}],
            allow_stub=False,
        )
    assert_role_output("contrarian", [{"attacks": [{"rationale": "x"}] * 6}], allow_stub=True)


def test_hangul_normalize_is_overlapping():
    from if_core.textutil import normalize_tokens
    assert "동시" in normalize_tokens("동시에")
    assert "시에" in normalize_tokens("동시에")


def test_publish_collect_fake_runner(tmp_path):
    from if_core.bus import ensure_jail, publish_collect
    run = tmp_path / "RUN-fake"
    run.mkdir()
    jail = ensure_jail(run, "LWAR1")
    (jail / "outbox" / "generate-r0.yaml").write_text("- local_id: LWAR1-01\n", encoding="utf-8")
    calls = []

    def runner(argv):
        calls.append(argv)
        if argv[0] == "send":
            return {"event": "task_published"}
        if argv[0] == "collect":
            return {"results": [{"lwar_id": "LWAR1", "status": "succeeded"}]}
        return {}

    accepted, obs = publish_collect(
        run, "generate", [("LWAR1", {"role": "generate", "stub": True})], 5, poll_s=0.01, runner=runner
    )
    assert "LWAR1" in accepted
    assert "succeeded" in obs
    assert any(c[0] == "send" and "--lwar-id" in c for c in calls)


def test_retry_lineage_and_outbox_paths():
    from if_core.bus import make_pao_task, outbox_rel, parse_round_n
    jail = Path("/tmp/jail")
    t0 = make_pao_task("RUN-1", "generate", "LWAR1", jail, "inbox/generate-r0.yaml",
                       outbox_rel("generate", 0), 0)
    assert t0["task_id"].endswith("-r0")
    assert t0["attempt"] == 1
    assert t0["expected_output"].endswith("generate-r0.yaml")
    assert "parent_task_id" not in t0
    t1 = make_pao_task("RUN-1", "generate", "LWAR1", jail, "inbox/generate-r1.yaml",
                       outbox_rel("generate", 1), 1, parent_task_id=t0["task_id"])
    assert t1["task_id"].endswith("-r1")
    assert t1["attempt"] == 2
    assert t1["parent_task_id"] == t0["task_id"]
    assert t1["adapter_options"]["retry_of"] == t0["task_id"]
    assert t1["expected_output"] != t0["expected_output"]
    assert parse_round_n(t1["task_id"]) == parse_round_n(t0["task_id"]) + 1


def test_if_oa_allows_validate():
    oa = Path(__file__).resolve().parents[2] / ".agents" / "skills" / "if-oa" / "scripts" / "if_oa.py"
    text = oa.read_text(encoding="utf-8")
    assert "validate" in text
    assert "control" in text
