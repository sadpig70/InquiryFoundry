"""The `review` role recommends; only a person closes.

`assert_transition` refuses ADOPTED unless the caller says actor="human", but
close_review says that unconditionally — the guard was procedural, held by
whoever filled review.yaml. Attaching a reviewer LWAR makes that assumption
load-bearing, so the guard has to live somewhere the code can enforce it:
apply_recommendation leaves `reviewer` empty, and preflight_close refuses a run
without one.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

CORE = Path(__file__).resolve().parents[2] / ".agents" / "skills" / "if-core"
sys.path.insert(0, str(CORE))

from if_core.compose import compose  # noqa: E402
from if_core.review import (  # noqa: E402
    apply_recommendation,
    close_review,
    open_review,
    ratify,
    review_packet,
)
from if_core.semantic import SemanticError, assert_role_output  # noqa: E402
from if_core.store import Blocked, Store  # noqa: E402


def _seed(local_id):
    return {
        "local_id": local_id,
        "question": "does the fitted exponent survive exact FLOP accounting?",
        "question_norm": "does the fitted exponent survive exact flop accounting %s" % local_id,
        "question_class": "phenomenon",
        "operator": "OP-BOUND",
        "unknown_type": "boundary",
        "unknown_ref": "U-RUN-R-1",
        "target_concepts": ["scaling laws"],
        "assumptions": ["the two papers minimise the same loss"],
        "unknowns": ["whether the exponent shifts"],
        "why_matters": "the accounting convention decides the reported exponent",
        "evidence": [{"source": "papers/kaplan2020",
                      "claim": "loss follows a power law in compute",
                      "confidence": 0.7}],
        "falsifier": "the exponent is unchanged under exact accounting",
        "minimal_test": {"variable": "fitted exponent",
                         "comparison": "approximate versus exact FLOP accounting",
                         "reject_if": "bootstrap interval within a plus or minus 0.03 band"},
        "action_plan": {"method": "data", "data": "published isoFLOP tables",
                        "metric": "fitted exponent",
                        "criterion": "bootstrap interval within the equivalence band"},
        "lineage": {"generated_by": "LWAR2", "evidence_kind": "papers",
                    "objective": "consensus_falsify", "run_id": "RUN-R",
                    "parents": [], "domain": "scaling"},
    }


def _decision_rows(store):
    text = store.decisions.read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


@pytest.fixture
def reviewed_run(tmp_path):
    store = Store(tmp_path)
    run_dir = tmp_path / "runs" / "RUN-R"
    run_dir.mkdir(parents=True)
    seeds = [_seed("LWAR2-01"), _seed("LWAR2-02")]
    dissent = {s["local_id"]: {"verdict": "SURVIVED", "local_id": s["local_id"],
                               "attacks": [{"dtype": "evidence", "result": "wound",
                                            "attack": "the tables disagree",
                                            "rationale": "different conventions"}]}
               for s in seeds}
    cards = {s["local_id"]: {"verdict": "PASS", "scores": {
        "impact": 0.8, "testability": 0.8, "grounding": 0.8, "actionability": 0.8}}
        for s in seeds}
    qos = compose(store, run_dir, "RUN-R", seeds, dissent, cards,
                  {"papers": ["papers/kaplan2020"]}, "normal")
    open_review(store, run_dir, "RUN-R", qos)
    (run_dir / "report.yaml").write_text(
        yaml.safe_dump({"run_id": "RUN-R", "mode": "normal",
                        "seed_count": 2, "qo_count": 2}),
        encoding="utf-8")
    return store, run_dir, qos


def _outbox(qos, decision="adopt", reason="the re-analysis runs on published tables"):
    return {"run_id": "RUN-R",
            "recommendations": [{"question_id": q["question_id"],
                                 "decision": decision, "reason": reason} for q in qos]}


def test_a_recommendation_cannot_close_a_run(reviewed_run):
    """The guard that matters. A reviewer LWAR fills every decision and the run
    still will not close, because `reviewer` is empty and preflight_close
    refuses that. Nothing here depends on the reviewer being honest."""
    store, run_dir, qos = reviewed_run
    out = apply_recommendation(run_dir, _outbox(qos), "fable-5")

    assert out["applied"] == 2
    doc = yaml.safe_load((run_dir / "review.yaml").read_text(encoding="utf-8"))
    assert doc["reviewer_kind"] == "machine_recommended"
    assert doc["recommended_by"] == "fable-5"
    assert doc["reviewer"] == ""
    assert all(d["decision"] == "adopt" for d in doc["decisions"])

    with pytest.raises(Blocked, match="reviewer required"):
        close_review(store, run_dir)


def test_ratifying_lets_it_close_and_records_who_decided(reviewed_run):
    """A person putting their name on it is what unlocks the run, and the log
    keeps the distinction: these reasons feed the next run's avoid_patterns."""
    store, run_dir, qos = reviewed_run
    apply_recommendation(run_dir, _outbox(qos), "fable-5")
    ratified = ratify(run_dir, "Jung Wook Yang")
    assert ratified["reviewer_kind"] == "human_ratified"

    result = close_review(store, run_dir)
    assert result["status"] == "closed"
    assert result["decided"]["adopt"] == 2

    rows = _decision_rows(store)
    assert rows and all(r["decided_by"] == "human_ratified" for r in rows)


def test_a_run_a_person_reviewed_directly_is_marked_human(reviewed_run):
    """No reviewer LWAR involved: the provenance must not silently claim one."""
    store, run_dir, qos = reviewed_run
    doc = yaml.safe_load((run_dir / "review.yaml").read_text(encoding="utf-8"))
    doc["reviewer"] = "Jung Wook Yang"
    for d in doc["decisions"]:
        d["decision"] = "reject"
        d["reason"] = "the premise is contradicted by the cited table"
    (run_dir / "review.yaml").write_text(
        yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")

    close_review(store, run_dir)
    rows = _decision_rows(store)
    assert rows and all(r["decided_by"] == "human" for r in rows)


def test_a_recommendation_must_cover_every_open_decision(reviewed_run):
    """A partial recommendation would leave `pending` rows that read as decided."""
    store, run_dir, qos = reviewed_run
    partial = _outbox(qos)
    partial["recommendations"] = partial["recommendations"][:1]
    with pytest.raises(Blocked, match="no recommendation for"):
        apply_recommendation(run_dir, partial, "fable-5")


def test_a_recommendation_for_another_run_is_refused(reviewed_run):
    store, run_dir, qos = reviewed_run
    wrong = _outbox(qos)
    wrong["run_id"] = "RUN-OTHER"
    with pytest.raises(Blocked, match="RUN-OTHER"):
        apply_recommendation(run_dir, wrong, "fable-5")


def test_a_verdict_without_an_argument_is_refused():
    """A reject reason becomes the next run's avoid_pattern, so an empty one is
    worse than no verdict at all."""
    good = {"recommendations": [{"question_id": "Q-1", "decision": "reject",
                                 "reason": "the cited appendix already settles this"}]}
    assert_role_output("review", good, allow_stub=False)

    for bad_reason in ("no", "TODO", "deterministic stub answer"):
        bad = {"recommendations": [{"question_id": "Q-1", "decision": "reject",
                                    "reason": bad_reason}]}
        with pytest.raises(SemanticError):
            assert_role_output("review", bad, allow_stub=False)


def test_the_reviewer_packet_carries_no_provenance(reviewed_run):
    """Vendor, operator and machine ranking say who wrote a question and how the
    pipeline ranked it — the two things an independent judgement must not lean
    on. open_review already refuses to leak them into review.yaml."""
    store, run_dir, _ = reviewed_run
    packet = review_packet(store, run_dir)
    blob = yaml.safe_dump(packet, allow_unicode=True)
    for leak in ("generated_by", "vendor_family", "operator", "scores", "LWAR2"):
        assert leak not in blob, leak
    assert packet["questions"][0]["question"]
    assert packet["questions"][0]["dissent"]


def test_the_packet_carries_the_run_constraints(tmp_path, reviewed_run):
    """Without them the reviewer judges feasibility in the abstract while the
    generator worked inside a stated envelope. Calibrating on RUN-20260820-live6
    the only feasibility split was exactly that: the operator deferred for want
    of cluster access, the reviewer adopted as runnable at accessible scale."""
    store, run_dir, _ = reviewed_run
    rule = "실행 계획은 공개 획득 가능한 데이터와 재현 가능한 규모만 사용한다."
    (run_dir / "brief.yaml").write_text(
        yaml.safe_dump({"brief_id": "RUN-R", "constraints": [rule]}, allow_unicode=True),
        encoding="utf-8")

    assert review_packet(store, run_dir)["constraints"] == [rule]

    # An explicit envelope overrides the run's own, for re-reviewing an older
    # run under rules its brief never carried.
    other = "비공개 프론티어 내부 로그를 전제하지 않는다."
    assert review_packet(store, run_dir, [other])["constraints"] == [other]

    # Still no provenance.
    blob = yaml.safe_dump(review_packet(store, run_dir), allow_unicode=True)
    for leak in ("generated_by", "vendor_family", "operator", "scores"):
        assert leak not in blob, leak


def test_a_run_without_constraints_yields_an_empty_envelope(tmp_path, reviewed_run):
    """Absent must mean empty, not a crash: live6 predates the field."""
    store, run_dir, _ = reviewed_run
    assert review_packet(store, run_dir)["constraints"] == []


def test_a_second_review_of_the_same_run_gets_its_own_round(reviewed_run, monkeypatch):
    """task_id is derived from (run_id, role, lwar, round_n) and the ledger
    refuses a repeat, so a second review collided on r0 and died with "task
    already has a ledger entry". Re-reviewing is a normal thing to want — a
    changed envelope, a second opinion — so the round advances by itself."""
    import if_core.review as review_mod

    store, run_dir, qos = reviewed_run
    (run_dir / "pao_drafts").mkdir(exist_ok=True)
    seen = []

    def fake_publish(rd, role, items, timeout_s, **kw):
        lwar_id, inbox = items[0]
        seen.append(inbox["round_n"])
        # publish_collect writes the draft; stand in for that so the next call
        # sees this round as taken.
        (rd / "pao_drafts" / ("review-%s-r%d.json" % (lwar_id, inbox["round_n"]))).write_text(
            "{}", encoding="utf-8")
        return {lwar_id: _outbox(qos)}, ["succeeded"]

    # request_review imports publish_collect from .bus at call time, so the
    # patch has to land on the bus module itself.
    import if_core.bus as bus_mod
    monkeypatch.setattr(bus_mod, "publish_collect", fake_publish)

    review_mod.request_review(store, run_dir, "LWAR9", "fable-5", apply=False)
    review_mod.request_review(store, run_dir, "LWAR9", "fable-5", apply=False)
    assert seen == [0, 1]

    out = review_mod.request_review(store, run_dir, "LWAR9", "fable-5",
                                    apply=False, round_n=7)
    assert out["round_n"] == 7
