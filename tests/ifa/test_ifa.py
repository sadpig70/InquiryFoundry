"""ifa unit tests — the invariants, not the happy path.

The pipeline is exercised end-to-end with a stub runner standing in for the
PAO bus: publish_collect's runner injection point means the whole cycle runs
against fixture outboxes without a mailbox, which is also how the bus copy's
matching logic stays honest — the stub returns stale and mismatched results
on purpose.
"""

import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / ".agents" / "skills" / "ifa-core"))

from ifa_core import cycle  # noqa: E402
from ifa_core.schema import (  # noqa: E402
    SchemaError,
    validate_adjudicate_outbox,
    validate_predict_outbox,
)
from ifa_core.store import IfaStore, atomic_write_yaml  # noqa: E402


# ---------------- fixtures ----------------

def make_stores(tmp_path, n_questions=2):
    """A scratch .if with adopted questions, and an empty .ifa beside it."""
    if_root = tmp_path / ".if"
    qdir = if_root / "graph" / "questions"
    qdir.mkdir(parents=True)
    for i in range(n_questions):
        q = {
            "question_id": f"Q-TEST-{i:04d}",
            "status": "ADOPTED",
            "question": f"test question {i} with enough text to matter",
            "falsifier": "some falsifier",
            "minimal_test": {"variable": "v", "comparison": "c",
                            "reject_if": f"difference exceeds 0.0{i + 1} margin band"},
            "lineage": {"domain": "preference" if i % 2 else "scaling",
                        "run_id": "RUN-X", "generated_by": "LWARX"},
        }
        atomic_write_yaml(qdir / f"{q['question_id']}.yaml", q)
    return IfaStore(str(tmp_path / ".ifa"), str(if_root))


def good_prediction(qid):
    return {
        "question_id": qid, "direction": "reject",
        "prediction": "the margin will be exceeded on the public split",
        "rationale": "x" * 80,
        "confidence": "medium",
        "kill_condition": "a flat curve across all checkpoints would kill this",
        "evidence": ["papers/rafailov2023"],
    }


def stub_runner_factory(run_dir, outbox_by_role):
    """Pretend bus: on send, write the prepared outbox; on collect, report
    success -- after first offering a STALE result that must be ignored."""
    state = {"sent": [], "collect_calls": 0}

    def runner(argv):
        if argv[0] == "send":
            lwar = argv[argv.index("--lwar-id") + 1]
            import json as _json
            task = _json.loads(Path(argv[argv.index("--task-file") + 1]).read_text(encoding="utf-8"))
            role = task["role"]
            doc = outbox_by_role.get(role, {}).get(lwar)
            if doc is not None:
                atomic_write_yaml(Path(run_dir) / "jail" / lwar / "outbox" / f"{role}.yaml", doc)
            state["sent"].append((role, lwar, task["task_id"]))
            return {"event": "task_published"}
        if argv[0] == "collect":
            state["collect_calls"] += 1
            results = []
            for role, lwar, tid in state["sent"]:
                # A stale leftover from some earlier task: same worker, wrong
                # task id. The matching rule must skip it (live10g lesson).
                results.append({"lwar_id": lwar,
                                "result": {"task_id": "task-ifa-STALE", "status": "succeeded"}})
                results.append({"lwar_id": lwar,
                                "result": {"task_id": tid, "status": "succeeded"}})
            return {"results": results}
        return {}

    return runner


def run_full(tmp_path, lwars=("LWAR1", "LWAR2", "LWAR4"), tamper=None):
    store = make_stores(tmp_path)
    run_id = "RUN-IFA-T1"
    run_dir = store.run_dir(run_id)
    batch = cycle.select_batch(store, 6)
    atomic_write_yaml(run_dir / "batch.yaml", batch)
    qids = [q["question_id"] for q in batch]

    predict = {l: [good_prediction(q) for q in qids] for l in lwars}
    if tamper:
        tamper(predict)
    outbox_by_role = {"predict": predict, "rebut": {}, "adjudicate": {}}

    # Two-phase stub: rebut/adjudicate outboxes depend on the minted anon ids,
    # so the runner fills them lazily by reading the inbox it was just sent.
    def lazy_runner(argv):
        if argv[0] == "send":
            import json as _json
            lwar = argv[argv.index("--lwar-id") + 1]
            task = _json.loads(Path(argv[argv.index("--task-file") + 1]).read_text(encoding="utf-8"))
            role = task["role"]
            jail = Path(run_dir) / "jail" / lwar
            if role == "rebut":
                inbox = yaml.safe_load((jail / "inbox" / "rebut.yaml").read_text(encoding="utf-8"))
                doc = [{"anon_id": p["anon_id"], "attack": "weakest link named here",
                        "result": "wounded"} for p in inbox["predictions"]]
                outbox_by_role["rebut"][lwar] = doc
            elif role == "adjudicate":
                inbox = yaml.safe_load((jail / "inbox" / "adjudicate.yaml").read_text(encoding="utf-8"))
                doc = [{"anon_id": c["anon_id"], "grounding": 0.7,
                        "consistency": 0.8, "falsifiability": 0.6}
                       for c in inbox["cases"]]
                outbox_by_role["adjudicate"][lwar] = doc
        return base_runner(argv)

    base_runner = stub_runner_factory(run_dir, outbox_by_role)
    report = cycle.run_predict_round(store, run_id, list(lwars), runner=lazy_runner)
    return store, run_id, report


# ---------------- tests ----------------

def test_never_writes_into_if(tmp_path):
    """Invariant 1: the question store is a window, not a surface."""
    store, run_id, report = run_full(tmp_path)
    assert report["status"] == "predicted"
    # Nothing under .if changed except what we created in the fixture.
    if_files = sorted(p.name for p in (Path(store.if_root) / "graph" / "questions").rglob("*"))
    assert if_files == ["Q-TEST-0000.yaml", "Q-TEST-0001.yaml"]
    with pytest.raises(PermissionError):
        store.assert_outside_if(Path(store.if_root) / "graph" / "x.yaml")


def test_kind_is_predicted_and_nothing_else(tmp_path):
    store, run_id, report = run_full(tmp_path)
    answers = store.load_answers(run_id)
    assert answers and all(a["kind"] == "predicted" for a in answers)
    bad = dict(answers[0], kind="answered", answer_id="ANS-XX-999")
    with pytest.raises(ValueError):
        store.write_answer(bad)


def test_rotation_forbids_self_examination(tmp_path):
    """The assignment table is written and no author rebuts or scores itself."""
    store, run_id, report = run_full(tmp_path)
    asg = yaml.safe_load((Path(store.root) / "runs" / run_id / "assignment.yaml")
                         .read_text(encoding="utf-8"))
    for stage in ("rebut", "adjudicate"):
        for examiner, source in asg["rotation"][stage].items():
            assert examiner != source, (stage, examiner)


def test_stale_results_do_not_satisfy_the_wait(tmp_path):
    """The stub offers a wrong-task-id result before every real one; if the
    matching rule regressed, collection would complete on garbage and the
    outboxes would be missing."""
    store, run_id, report = run_full(tmp_path)
    assert report["status"] == "predicted"
    assert "timed_out" not in report["statuses"]


def test_invalid_predict_outbox_drops_that_vendor_only(tmp_path):
    def tamper(predict):
        predict["LWAR2"] = [{"question_id": "Q-TEST-0000"}]  # everything missing
    store, run_id, report = run_full(tmp_path, tamper=tamper)
    assert report["status"] == "predicted"          # two valid vendors remain
    assert any(d["lwar_id"] == "LWAR2" and d["role"] == "predict"
               for d in report["dropped"])
    authors = {a["prediction"]["question_id"] and a for a in []}  # noqa: F841
    assert "LWAR2" not in report["vendors"]


def test_registered_requires_reviewer_and_ratification(tmp_path):
    store, run_id, report = run_full(tmp_path)
    answers = store.load_answers(run_id)
    outbox = [{"answer_id": a["answer_id"], "decision": "register",
               "reason": "well grounded"} for a in answers]
    cycle.fold_review(store, run_id, outbox, "Stub Reviewer")
    with pytest.raises(PermissionError):
        cycle.close_run(store, run_id)              # reviewer still empty
    cycle.ratify(store, run_id, "Stub Reviewer", delegated=True)
    out = cycle.close_run(store, run_id)
    assert out["decided"]["register"] == len(answers)
    assert all(a["status"] == "REGISTERED" for a in store.load_answers(run_id))


def test_priorities_rank_split_first(tmp_path):
    store, run_id, report = run_full(tmp_path)
    answers = store.load_answers(run_id)
    # Make one question split: flip one vendor's direction before review.
    flip_q = answers[0]["question_id"]
    flipped = False
    for a in answers:
        if a["question_id"] == flip_q and not flipped:
            a["prediction"]["direction"] = "no-reject"
            store.write_answer(a)
            flipped = True
    outbox = [{"answer_id": a["answer_id"], "decision": "register",
               "reason": "ok"} for a in answers]
    cycle.fold_review(store, run_id, outbox, "Stub")
    cycle.ratify(store, run_id, "Stub", delegated=True)
    cycle.close_run(store, run_id)
    rows = cycle.priorities(store, run_id)
    assert rows[0]["question_id"] == flip_q
    assert rows[0]["disagreement"] == "split"


def test_second_opinion_targets_exactly_the_singles(tmp_path):
    """The mode exists to fill the holes the first walk left: questions with
    one registered prediction get a second opinion; fully-covered and
    never-predicted questions are both out of scope."""
    store, run_id, report = run_full(tmp_path)
    answers = store.load_answers(run_id)
    # Register one prediction for question 0, all three for question 1.
    q0 = answers[0]["question_id"]
    outbox = []
    kept_one = False
    for a in answers:
        if a["question_id"] == q0:
            d = "register" if not kept_one else "discard"
            kept_one = True
        else:
            d = "register"
        outbox.append({"answer_id": a["answer_id"], "decision": d, "reason": "r"})
    cycle.fold_review(store, run_id, outbox, "Stub")
    cycle.ratify(store, run_id, "Stub", delegated=True)
    cycle.close_run(store, run_id)
    so = cycle.select_batch(store, 99, "second-opinion")
    assert [q["question_id"] for q in so] == [q0]
    assert cycle.select_batch(store, 99, "fresh") == []


def test_schema_rejects_thin_and_novel(tmp_path):
    with pytest.raises(SchemaError):
        validate_predict_outbox([dict(good_prediction("Q-1"), rationale="short")], {"Q-1"})
    with pytest.raises(SchemaError):
        validate_adjudicate_outbox(
            [{"anon_id": "P-x", "grounding": 0.5, "consistency": 0.5,
              "falsifiability": 0.5, "novelty": 0.9}], {"P-x"})
