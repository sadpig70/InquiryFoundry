# InquiryFoundry Design @v:0.2.3

**Status** designing · **Notation** PG v1.4 + PGF v2.6 · **Scale** Level 3 (22 nodes)
**Runtime** Claude Code CLI OA + 이종 CLI LWAR (PAO file bus)
**Draft sources (non-normative)** `_legacy/InquiryFoundry_DESIGN.md`, `_legacy/*`
**Review** `.pgf/REVIEW-InquiryFoundry.md` (design-review cycle 3 applied)
**Upgrade input** `_workspace/IF_upgrade_plan.md` (D19–D21 accepted)

이 문서가 InquiryFoundry의 권위 설계다. 초안은 아이디어 원천일 뿐 노드·스키마·게이트의 출력이 아니다.

---

## Purpose

InquiryFoundry(IF)는 다종 런타임이 **가시성 감옥 안에서** 미지를 탐지하고, 질문 공간 연산자로 변환한 뒤, 반론·게이트·블라인드 평가를 거쳐 **검증·추적·실행 가능한 Question Object** 포트폴리오를 만든다.

```text
value ≈ expected_knowledge_change × importance × answerability
output = Pareto portfolio of Question Objects, not Best Answer
MVP unknowns = known_unknown | contradictory   # 나머지 8종은 Phase 2
protocol_valid = computed from observations (see IfCycle). never a constant.
```

설치 단위는 폴더 복사 스킬이다. 실행 단위는 사람이 띄운 LWAR + OA의 메일박스 발행이다.

---

## Closed Decisions

| ID | Decision |
|---|---|
| D1 | 태스크 버스는 기존 PAO(`PAO_ROOT` 또는 `<cwd>/.pao`). IF 데이터는 `IF_ROOT`(기본 `<cwd>/.if`). 런타임 포크 금지. |
| D2 | 스킬 경로: `.agents/skills/if-*`. |
| D3 | PAO `task.schema.json`에 `payload`가 없다. IF 입력은 inbox YAML. PAO 태스크는 `role` + `input_files` + `expected_output` + `adapter_options.if_*`. `completion_criteria`는 파일 존재 + 스키마 패스만. |
| D4 | MVP 다양성: `question_norm` 토큰 Jaccard. `target_concepts` 제외. 마지막 라운드 강제 수용 금지. |
| D5 | 인간 리뷰는 `review.yaml`. 점수·`generated_by`·model 비노출. 대시보드는 Phase 3. |
| D6 | Compose는 LWAR 역할이 아니다. **IfCycle의 결정론 조립**이다. IfOa는 PAO CLI 어댑터만. |
| D7 | 기계 게이트: `G-GROUND`, `G-CLEAR`, `G-PATH`, `G-TESTSHAPE`. 인간: `G-DUP`, `G-UNKNOWN`, `G-ACTION`, `G-SAFETY`. `normative`/`meta`는 MVP에서 SCORED 불가(DORMANT). |
| D8 | 정상 InquiryCycle은 LWAR ≥ 3 (생성 ≠ 반론 ≠ 심사). LWAR=2는 `brief.mode=ablation`만. ablation은 `ADOPTED` 금지, `protocol_valid=false`. LWAR&lt;2 실행 금지. |
| D9 | `question_class` ≠ `operator`. |
| D10 | `ADOPTED`는 `review.yaml.reviewer` 비공란에서만 도출. 런 게이트는 포트폴리오 산출이지 채택 건수가 아니다. |
| D11 | Generate 입력은 미지 리스트다. topic→question 자유 경로 없음. MVP `mine_min`은 `known_unknown`+`contradictory`만. 출처 완비·모순 0이면 빈 탐사지 `seed_count==0` fail. |
| D12 | Judge 기록 축: testability, grounding, actionability (+선택 impact 루브릭). Pareto 축은 `{testability, actionability, grounding}`만. `novelty`/`diversity_contribution` 키 없음. |
| D13 | `question_id`는 IfCycle 프로세스의 StoreIo만 mint. Generate는 `local_id`만 쓴다. Compose가 `local_id → question_id`를 붙인다. |
| D14 | 진입점: OA 세션이 `python .agents/skills/if-core/scripts/if_cycle.py run|close`를 실행한다. IfOa는 PAO CLI 래퍼만. 사이클 프로세스 = PAO writer(`PAO_OA_ID`). |
| D15 | Judge outbox 스키마에 `question_id` 없음. `rekey`는 IfCycle만 수행. |
| D16 | `dissent_portfolio==[]`는 wound/kill 로그가 0이면 정상. 로그에 있는데 목록이 비면 `incomplete`. |
| D17 | Worker `cwd`+`permissions.read/write`는 jail 트리(`inbox/{own}`, `hints/{own}`, `outbox/{own}`)만. `graph/` 워커 접근 금지. |
| D18 | AI가 evidence를 안 내면 시드 drop. `source_hint`로 evidence를 날조하지 않는다. |
| D19 | 기계 kill 1건 = `KILLED` (`kills >= 1`). AI는 kill을 부여하지 않는다. |
| D20 | `th_pair`는 **런 내부 쌍**에만. prior(도메인 일치 + 최근 50 SCORED/ADOPTED)는 **mean만**. `th_mean` 기본 0.40, `th_pair` 기본 0.55 (`th_mean < th_pair`). |
| D21 | 기계 `REJECTED` 카드는 informational. 인간 adopt 불가. reason은 `record_decision`만. `LEGAL[REJECTED]`는 DORMANT만. |

---

## Invariants

1. **Independent First** — 워커 jail 밖 경로(`allocation.yaml`, 타 outbox, `graph/`, `memory/`) 열기 = `protocol_error`. PAO `permissions.read`가 jail만 가리킨다.
2. **Skill ≠ Heterogeneity** — 배분표가 이종성을 만든다. `vendor_family` 미기재는 register 거절. 전원 동일 family면 정상 런 `blocked`.
3. **No Self-Judge** — 생성자는 그 질문의 contrarian/judge가 될 수 없다. 정상 런은 반론자≠심사자.
4. **No LLM Novelty** — ScoreCard에 `novelty` 키 또는 미선언 숫자 키가 있으면 카드 폐기.
5. **Dissent Lives** — KILLED도 QO stub + dissent_log. wound/kill ≥ 1(DORMANT 포함)은 `dissent_portfolio`에 있어야 close 가능. 0건이면 빈 목록으로 close 가능. 기계 REJECTED는 informational.
6. **Human Gate** — 기계는 `ADOPTED`를 쓰지 않는다. `actor=human`은 reviewer 비공란에서만.
7. **Provenance** — lineage 필수 공란이면 StoreIo 거절. 그래프 쓰기와 `question_id` mint는 StoreIo 단일 진입(IfCycle/OA 프로세스).
8. **Overlay, not Fork** — `if-oa`/`if-lwar`는 PAO CLI 호출. `pao_runtime` 복사 금지.

---

## Gantree

```
InquiryFoundry // 검증 가능한 질문 포트폴리오 시스템 (designing) @v:0.2.3
    IfCore // 규약 + 결정론 I/O. 역할 스킬 아님 (designing)
        SchemaPack // Brief/Seed/QO/Report/Review/Bus YAML 스키마 (designing)
        OperatorPack // 질문 공간 변환 12종 + 제안 절차 (designing)
        GatePack // 기계/인간 게이트와 테스트 형상 (designing)
        StatePack // Seed 수명 + QO 상태머신 + 전이 주체 (designing)
        StoreIo // id lock, QO/edges/memory/run I/O (designing) @dep:SchemaPack,StatePack
        BusContract // PAO envelope, publish_collect, jail cwd (designing) @dep:SchemaPack
    IfRuntime // PAO 오버레이만 (designing) @dep:IfCore
        IfOa // send/collect/recover/status/presence/audit-health. 도메인 쓰기 금지 (designing) @dep:BusContract
        IfLwar // begin → dispatch → result-file complete (designing) @dep:BusContract
    IfRoles // 인지 역할. IfCore 스키마만 의존 (designing) @dep:IfCore
        IfGenerate // mine_min 2종 → operator. local_id만 (designing) @dep:OperatorPack
        IfContrarian // 6유형 반론. kill은 기계 규칙만 (designing)
        IfJudge // 블라인드 게이트 + 루브릭. novelty 키 금지 (designing) @dep:GatePack
        IfPhase2Roles // unknown-miner/novelty/action/safety (blocked) @dep:HumanClose
    IfCycle // if_cycle.py run|close. 런 소유자 (designing) @dep:IfRuntime,IfGenerate,IfContrarian,IfJudge
        Allocate // 4차원 이종 배분. 기본은 결정론 로테이션 (designing) @dep:OperatorPack,StoreIo
        ExploreLoop // generate 병렬 + Jaccard 발산 (designing) @dep:Allocate,IfGenerate
        ExploitLoop // contrarian → judge (designing) @dep:ExploreLoop,IfContrarian,IfJudge
        Compose // local_id→Q-id, 그래프 유일 작성 (designing) @dep:ExploitLoop,StoreIo
        HumanClose // review.yaml 1차 종료, close 재개 (designing) @dep:Compose
```

---

## Layout

```text
.agents/skills/
    if-core/     # schemas/, operators/, gates/, scripts/store.py, scripts/bus.py
                 # scripts/if_cycle.py   # entry: run | close  (OA session)
    if-oa/       # scripts/if_oa.py → pao-oa CLI only
    if-lwar/     # scripts/if_lwar.py → begin / complete --result-file
    if-generate/
    if-contrarian/
    if-judge/

$IF_ROOT/                    # default <cwd>/.if
    graph/questions/Q-*.yaml
    graph/revisions/
    graph/.idseq             # {date: YYYYMMDD, n: int}
    graph/edges.jsonl
    memory/decisions.jsonl
    dissent/dissent_log.jsonl
    runs/RUN-YYYYMMDD-N/
        brief.yaml
        allocation.yaml      # OA only. 워커 가시 경로 금지
        jail/{lwar_id}/      # cwd + permissions 경계
            inbox/{task_id}.yaml
            hints/           # 그 LWAR 슬라이스만 복사
            outbox/{task_id}.yaml
        inbox/{task_id}.yaml     # OA 원본 (워커 비가시)
        outbox/{task_id}.yaml
        review.yaml
        report.yaml
        local_id_map.yaml    # local_id -> question_id (compose 멱등)
        run_nonce            # 32 bytes. 워커 비가시. anon HMAC 키
```

---

## PPR

```python
QuestionClass = Literal["phenomenon", "cause", "scenario", "design", "normative", "meta"]
UnknownType = Literal[
    "known_unknown", "contradictory", "hidden_assumption", "measurement",
    "causal", "boundary", "cross_domain_gap", "temporal", "emergent",
    "unknown_unknown_candidate",
]
OperatorId = Literal[
    "OP-CONTRA", "OP-INVERT", "OP-BOUND", "OP-SCALE", "OP-XDOM", "OP-MISSVAR",
    "OP-CAUSAL", "OP-MEASURE", "OP-CF", "OP-2ND", "OP-ADV", "OP-REGIME",
]
EvidenceKind = Literal["papers", "patents", "code", "news", "failures", "regulation", "history"]
ObjectiveId = Literal["importance_max", "consensus_falsify", "info_per_cost"]
QStatus = Literal[
    "DRAFT", "SCORED", "REVIEWED",
    "ADOPTED", "REJECTED", "DEFERRED", "MERGED", "DORMANT", "QUARANTINE",
]
DissentType = Literal["evidence", "logic", "premise", "alternative", "stakeholder", "execution"]
AttackResult = Literal["miss", "wound", "kill"]
IfRole = str          # MVP: generate|contrarian|judge. 확장 시 테이블에 추가
Phase = Literal["EXPLORE", "EXPLOIT"]
RunMode = Literal["normal", "ablation"]
```

### SchemaPack

```python
def schema_pack() -> None:
    """if-core/schemas/*.yaml 단일 출처."""

    brief = {
        "brief_id": "RUN-YYYYMMDD-N",
        "mode": RunMode,                    # default normal
        "domain": str,
        "goal": Literal["discovery", "validation", "strategy", "risk", "invention"],
        "constraints": list[str],
        "forbidden_premises": list[str],
        "must_consider_slices": dict[str, list[str]],  # lwar_id -> 분할 항목. 전체 공유 금지
        "success_criteria": str,
        "evidence_hints": dict[EvidenceKind, list[str]],
        "budget": {"max_rounds": 3, "max_seeds_per_lwar": 8},
    }

    claim = {"claim_id": str, "text": str, "source": Optional[str]}

    unknown = {
        "id": str,                          # U-{run}-{n}  IfCycle이 부여
        "unknown_type": Literal["known_unknown", "contradictory"],  # MVP
        "statement": str,
        "claim_ids": list[str],             # 비면 무효
        "source_hint": Optional[str],
    }

    seed = {
        "local_id": str,                    # "{lwar_id}-{seq}" 워커 발급
        "question_id": Optional[str],       # Compose/StoreIo mint 전엔 없음
        "question": str,
        "question_norm": str,
        "question_class": QuestionClass,
        "operator": OperatorId,
        "unknown_type": UnknownType,
        "unknown_ref": str,                 # Unknown.id 필수
        "target_concepts": list[str],
        "why_matters": str,
        "assumptions": list[str],
        "unknowns": list[str],
        "evidence": list[{"source": str, "claim": str, "confidence": float}],
        "falsifier": str,
        "minimal_test": {                   # G-TESTSHAPE
            "variable": str,
            "comparison": str,
            "reject_if": str,
        },
        "action_plan": {
            "method": Literal["observe", "experiment", "data", "simulation"],
            "data": str,
            "metric": str,
            "criterion": str,
        },
        "lineage": {
            "generated_by": str,
            "evidence_kind": EvidenceKind,
            "objective": ObjectiveId,
            "run_id": str,
            "parents": list[str],
            "domain": str,
        },
    }

    qo = {**seed, "version": int, "status": QStatus,
          "contradictions": list[str],
          "estimated_cost": str,
          "scores": {
              "impact": Optional[float],
              "testability": Optional[float],
              "actionability": Optional[float],
              "grounding": Optional[float],
          },
          "gate_results": dict,
          "dissent": list,
          "human_review": {"status": str, "reviewer": str, "note": str},
          "created_at": str, "last_verified_at": str}

    dissent_report_outbox = {               # contrarian 워커. question_id 금지
        "local_id": str, "examiner": str,
        "attacks": list[{"dtype": DissentType, "attack": str,
                         "result": AttackResult, "rationale": str,
                         "kill_rule": Optional[str]}],
        "kill_count": int,
        "verdict": Literal["SURVIVED", "KILLED"],
    }
    dissent_report = {**dissent_report_outbox, "question_id": str, "run_id": str}

    score_card_outbox = {                   # judge가 씀. question_id 금지
        "anon_id": str,
        "verdict": Literal["SCORED", "GATE_FAIL"],
        "failed_gate": Optional[str],
        "scores": dict,
        "notes": str,
    }
    score_card = {                          # IfCycle rekey 이후 내부
        **score_card_outbox,
        "question_id": str,
        "local_id": str,
    }

    review = {
        "run_id": str, "reviewer": str,
        "portfolio": list[str],
        "all_scored": list[str],            # 점수 없이 id. 인간 누락 감사
        "dissent_portfolio": list[str],
        "decisions": list[{"question_id": str,
                           "decision": Literal["adopt", "reject", "defer", "pending"],
                           "reason": str,
                           "informational": bool,   # D21: 기계 REJECTED
                           "bucket": Literal["pareto", "dissent", "informational"],
                           "checks": {
                               "already_answered": Optional[bool],
                               "test_runnable": Optional[bool],
                               "duplicate": Optional[bool],
                           }}],
    }
    decision_rec = {"ts": str, "question_id": str, "decision": str,
                    "reason": str, "domain": str, "run_id": str,
                    "informational": bool}

    edges_rec = {"ts": str, "src": str, "rel": Literal["parent", "derived_from", "contradicts"],
                 "dst": str}
    report = {
        "run_id": str, "mode": RunMode, "separation": Literal["full", "ablation"],
        "protocol_valid": bool,             # hypothesis_valid 의 권위 이름
        "hypothesis_valid": bool,           # alias == protocol_valid
        "seed_count": int, "qo_count": int,
        "scored_count": int, "human": str, "dissent_referenced": bool,
        "slo_scored_ge_8": bool,
        "contributing_generate_lwars": int,
        "observed_statuses": list[str],
        "decided": Optional[dict],          # close 후 {adopt, reject, defer}
    }
    # acceptance_criteria:
    #   - scores 에 novelty, diversity_contribution 키 없음
    #   - judge/contrarian outbox 스키마에 question_id 없음
    #   - PAO task/result 스키마 무수정
    #   - must_consider 전역 리스트 없음 (슬라이스만)
```

### OperatorPack

```python
OPERATORS = [
    ("OP-CONTRA",  "A와 B가 동시에 참일 수 없는 이유는?"),
    ("OP-INVERT",  "A의 핵심 가정이 거짓이면 무엇이 일어나는가?"),
    ("OP-BOUND",   "A는 어떤 조건에서 더 이상 성립하지 않는가?"),
    ("OP-SCALE",   "A가 규모 1000배가 되면 어떤 새 현상이 나타나는가?"),
    ("OP-XDOM",    "타 영역 원리 X를 A에 적용하면?"),
    ("OP-MISSVAR", "현재 설명이 빠뜨린 변수는?"),
    ("OP-CAUSAL",  "A-B 상관을 만드는 실제 원인은?"),
    ("OP-MEASURE", "A를 잘못 측정하고 있지는 않은가?"),
    ("OP-CF",      "A가 없었다면 B는 발생했는가?"),
    ("OP-2ND",     "A 성공의 2차 효과는?"),
    ("OP-ADV",     "A를 실패시키는 가장 싼 방법은?"),
    ("OP-REGIME",  "환경이 바뀌면 기존 규칙은 언제 역전되는가?"),
]

def default_ops_for(index: int, k: int = 3) -> list[OperatorId]:
    n = len(OPERATORS)
    return [OPERATORS[(index * k + j) % n][0] for j in range(k)]

def leftover_ops(used_keys: set, family: str, ev: EvidenceKind, preferred: list) -> list:
    for shift in range(len(OPERATORS)):
        ops = default_ops_for(shift, 3)
        if (family, frozenset(ops), ev) not in used_keys:
            return ops
    return None  # caller must change ev or block
```

### GatePack

```python
MECH = ("G-GROUND", "G-CLEAR", "G-PATH", "G-TESTSHAPE")
HUMAN = ("G-DUP", "G-UNKNOWN", "G-ACTION", "G-SAFETY")

def distinct_content(plan: dict) -> bool:
    vals = [plan.get(k, "") for k in ("method", "data", "metric", "criterion")]
    return len(set(vals)) == 4 and all(len(v) >= 4 for v in vals)

def source_in_hints(source: str, hints: list[str]) -> bool:
    """부분문자열. 힌트 길이 < 6 은 무시 (만능 통과 방지)."""
    return any(h and len(h) >= 6 and (h in source or source in h) for h in hints)

def mechanical_gates(seed: dict, hints: list[str]) -> dict[str, str]:
    r = {}
    ev = seed.get("evidence") or []
    r["G-GROUND"] = "pass" if ev and all(
        e.get("source") and e.get("claim") and source_in_hints(e["source"], hints)
        for e in ev
    ) else "fail"
    r["G-PATH"] = "pass" if (seed.get("action_plan") or {}).get("method") in {
        "observe", "experiment", "data", "simulation"
    } else "fail"
    mt = seed.get("minimal_test") or {}
    r["G-TESTSHAPE"] = "pass" if all(mt.get(k) for k in ("variable", "comparison", "reject_if")) else "fail"
    filled = bool(seed.get("target_concepts") and seed.get("assumptions") and seed.get("unknowns"))
    r["G-CLEAR"] = "pass" if filled else "fail"
    plan = seed.get("action_plan") or {}
    if r["G-PATH"] == "pass" and not distinct_content(plan):
        r["G-PATH"] = "fail"
    for g in HUMAN:
        r[g] = "human"
    return r
    # acceptance_criteria:
    #   - G-FALSIFY 라는 이름은 없음 (G-TESTSHAPE 로 대체)
    #   - HUMAN 게이트를 mechanical fail 로 강제하지 않음
    #   - question_class in {normative, meta} 이면 Compose 가 SCORED 금지
```

### StatePack

```python
# Seed (jail outbox): local_id only
# QO 첫 write 는 항상 DRAFT. 같은 트랜잭션에서 한 번 더 전진.
# GATED 상태 없음 (기계 통과는 SCORED, 실패는 REJECTED).
#
# 액터
#   compose:  first DRAFT, then SCORED|REJECTED|DORMANT|MERGED
#   human:    SCORED -> REVIEWED -> ADOPTED|REJECTED|DEFERRED
#             REVIEWED 와 최종 모두 actor=human, reviewer_ok
#             최종(ADOPTED|REJECTED|DEFERRED)만 no-op. REVIEWED 는 final 재적용
#             기계 REJECTED 는 informational — 인간 전이 없음 (D21)
#   phase2:   SCORED|REVIEWED|ADOPTED|REJECTED|DEFERRED -> QUARANTINE only
#   store:    비포트폴리오 SCORED 는 그대로 둔다 (버그 아님)

LEGAL = {
    "DRAFT": {"SCORED", "REJECTED", "DORMANT", "MERGED", "QUARANTINE"},
    "SCORED": {"REVIEWED", "QUARANTINE", "MERGED", "DORMANT"},
    "REVIEWED": {"ADOPTED", "REJECTED", "DEFERRED", "QUARANTINE"},
    "DEFERRED": {"SCORED", "DORMANT", "REVIEWED"},
    "DORMANT": {"DRAFT", "SCORED"},
    "REJECTED": {"DORMANT"},
    "MERGED": set(),
    "ADOPTED": set(),
    "QUARANTINE": {"REVIEWED", "REJECTED"},
}

PHASE2_ALLOWED_FROM = {"SCORED", "REVIEWED", "ADOPTED", "REJECTED", "DEFERRED"}

def assert_transition(old, new, actor, reviewer_ok: bool) -> None:
    if actor == "phase2":
        if old not in PHASE2_ALLOWED_FROM or new != "QUARANTINE":
            raise ValueError("illegal phase2 transition")
        return
    if new not in LEGAL[old]:
        raise ValueError(f"illegal {old}->{new}")
    if new == "ADOPTED" and not (actor == "human" and reviewer_ok):
        raise ValueError("ADOPTED requires human reviewer")
```

### StoreIo

```python
IDLOCK = "$IF_ROOT/graph/.idlock"     # O_CREAT|O_EXCL, timeout_s=10
IDSEQ  = "$IF_ROOT/graph/.idseq"      # yaml {date, n}

def alloc_question_id(run_id: str) -> str:
    """IfCycle 프로세스만 호출. 워커·IfGenerate 금지. lock 구간은 +1 만."""
    date = run_id.split("-")[1][:8]    # RUN-YYYYMMDD-N
    with file_lock(IDLOCK, timeout_s=10):
        seq = load_yaml(IDSEQ) or {"date": date, "n": 0}
        if seq["date"] != date:
            seq = {"date": date, "n": 0}
        seq["n"] += 1
        atomic_write(IDSEQ, seq)
    return f"Q-{date}-{seq['n']:04d}"

def write_question(q: dict, actor: str, reviewer_ok: bool = False) -> str:
    validate(q)
    prev = load_optional(q["question_id"])
    if prev:
        assert_transition(prev["status"], q["status"], actor, reviewer_ok)
        q["version"] = prev.get("version", 1) + 1
        q["last_verified_at"] = now()
        archive_revision(prev)
    else:
        if q["status"] != "DRAFT":
            raise ValueError("first write must be DRAFT")
        q["version"] = 1
        q.setdefault("created_at", now())
        q.setdefault("last_verified_at", now())
    require_lineage(q)
    atomic_write(f"$IF_ROOT/graph/questions/{q['question_id']}.yaml", q)
    append_edges(q)
    return q["question_id"]

def append_edges(q: dict) -> None:
    """(src, rel, dst) 가 이미 있으면 skip."""
    seen = load_edge_keys()
    def add(rel, dst):
        key = (q["question_id"], rel, dst)
        if dst and key not in seen:
            append_jsonl(EDGES, edge(q["question_id"], rel, dst))
            seen.add(key)
    for p in q.get("lineage", {}).get("parents") or []:
        add("parent", p)
    for d in q.get("derived_from") or []:
        add("derived_from", d)
    for c in q.get("contradictions") or []:
        add("contradicts", c)

def reuse_or_mint(run, local_id: str, run_id: str) -> str:
    """runs/{run}/local_id_map.yaml. 재실행 시 같은 Q-id."""
    mp = load_yaml(run / "local_id_map.yaml") or {}
    if local_id in mp:
        return mp[local_id]
    qid = alloc_question_id(run_id)
    mp[local_id] = qid
    atomic_write(run / "local_id_map.yaml", mp)
    return qid

def query_avoid_patterns(domain: str, n: int = 8) -> list[str]:
    """결정론: 최근 reject reason 원문 n개. 군집은 하지 않음."""
    rows = [r for r in load_decisions()
            if r.get("decision") == "reject" and r.get("domain") == domain]
    return [r["reason"] for r in rows[-n:] if r.get("reason")]
    # acceptance_criteria:
    #   - StoreIo 에 AI_ 없음
    #   - first write 가 DRAFT 가 아니면 거절
    #   - alloc_question_id 호출자가 IfCycle 가 아니면 거절 (테스트 V9)
```

### BusContract

```python
VISIBLE = {
    "generate": ["jail/{own_lwar}/inbox/**", "jail/{own_lwar}/hints/**"],
    "contrarian": ["jail/{own_lwar}/inbox/**"],
    "judge": ["jail/{own_lwar}/inbox/**"],
}
FORBIDDEN_ANY = ["allocation.yaml", "graph/", "memory/", "runs/*/inbox/", "runs/*/outbox/"]

PAO_CRITERIA = [
    "expected_output file exists",
    "expected_output validates against if outbox schema for task.role",
]

OUTBOX_ENVELOPE = {
    "generate":   "list[seed_outbox]",              # local_id only
    "contrarian": "list[dissent_report_outbox]",
    "judge":      "list[score_card_outbox]",
}
ACCEPT_STATUS = {"succeeded"}
OMIT_STATUS = {"failed", "blocked", "cancelled", "interrupted",
               "timed_out", "protocol_error"}

def phase_of(role: str) -> str:
    return {"generate": "EXPLORE", "contrarian": "EXPLOIT", "judge": "EXPLOIT"}[role]

def path_allowed(allowed: list[str], lwar_id: str, opened_path: str) -> bool:
    """절대경로 정규화 후 glob/접두사 매칭. own_lwar 치환."""
    ...

def jail_dir(run, lwar_id: str) -> str:
    return f"{run}/jail/{lwar_id}"

def ensure_jail(run, lwar_id: str) -> str:
    """inbox/, hints/, outbox/ 3종 생성. send cwd 존재 보장."""
    j = jail_dir(run, lwar_id)
    for sub in ("inbox", "hints", "outbox"):
        mkdir(f"{j}/{sub}")
    return j

def propose_task_id(run_id, role, lwar_id, round_n: int) -> str:
    return f"task-if-{run_id}-{role}-{lwar_id}-r{round_n}"

def make_pao_task(run_id, role, lwar, jail, inbox_rel, outbox_rel, round_n=0) -> dict:
    """PAO task JSON. cwd=jail. complete 는 --result-file."""
    timeout = {"generate": 900, "contrarian": 600, "judge": 600}[role]
    return {
        "task_id": propose_task_id(run_id, role, lwar, round_n),
        "role": role,
        "goal": f"IF {role} for {run_id}",
        "instructions": f"cwd is jail. Read {inbox_rel}. Write {outbox_rel}.",
        "cwd": jail,
        "input_files": [f"{jail}/{inbox_rel}"],
        "expected_output": f"{jail}/{outbox_rel}",
        "timeout_s": timeout,
        "permissions": {
            "read": [jail_or_inbox, *trusted_if_skill_roots],
            "write": [f"{jail}/outbox"],
            "network": False,                 # Phase 2 novelty 만 True
        },
        # trusted_if_skill_roots = .agents/skills/if-lwar + if-core
        # Data jail remains inbox/hints/outbox. Skill import is not data visibility.
        "completion_criteria": PAO_CRITERIA,
        "adapter_options": {"if_run_id": run_id, "if_phase": phase_of(role),
                            "if_schema": "if.task.v1"},
    }

def publish_collect(run, role, items, lwars, timeout_s) -> tuple:
    """
    items: list of (lwar_id, inbox_yaml)
    1. ensure_jail + write inbox yaml
    2. oa.py send --lwar-id {id} --task-file <pao json>
    3. poll oa.py collect every 15s until all terminal or timeout_s
    4. status==succeeded 만 수용. 그 외 터미널은 omit
    5. recover stale lease once, then omit
    return (accepted: {lwar_id: outbox}, observed_statuses: list[str])
    """
    # acceptance_criteria:
    #   - collect 1회 스캔을 대기로 오해하지 않음
    #   - --auto 사용 금지. --lwar-id 필수
    #   - generate timeout_s 기본 900
```

### IfOa

```python
def if_oa(cmd: Literal["send", "collect", "recover", "status",
                       "presence", "audit-health",
                       "validate", "workflow-status", "control"]) -> dict:
    """PAO CLI 래퍼. doctor 없음. if_cycle / write_question 호출 금지."""
    return sh(f"python .agents/skills/pao-oa/scripts/oa.py {cmd} ...")
    # acceptance_criteria:
    #   - if-oa 폴더에 pao_runtime 없음
    #   - 그래프·review 파일을 쓰지 않음
    #   - if_cycle.py 가 이 래퍼를 호출한다. 역방향 금지
    #   - 런 전 건전성 = status + presence + audit-health
```

### IfLwar

```python
ROLE_SKILL = {"generate": "if-generate", "contrarian": "if-contrarian", "judge": "if-judge"}

def skill_dispatch(task_env: dict) -> None:
    """begin → 역할 실행 → result.yaml 기록 → complete --result-file."""
    tokens = sh("python .agents/skills/pao-lwar/scripts/lwar.py begin ...")
    inbox_path = task_env["input_files"][0]
    assert_visible(current_lwar(), task_env["role"], inbox_path)
    inbox = read_yaml(inbox_path)
    if task_env["role"] == "judge":
        assert current_lwar() not in inbox.get("exclude_lwars", [])
        for q in inbox["questions"]:
            assert "generated_by" not in (q.get("lineage") or {})
            assert "question_id" not in q
            assert "operator" not in q
            assert "local_id" not in q
    out = load_skill(ROLE_SKILL[inbox["role"]]).run(inbox)
    write_yaml(task_env["expected_output"], out)
    result_path = write_result_yaml(status="succeeded", summary=inbox["role"],
                                    artifacts=[task_env["expected_output"]],
                                    evidence={}, next_action="none",
                                    **tokens)
    sh("python .agents/skills/pao-lwar/scripts/lwar.py complete "
       "--identity-file ... --task-id ... --claim-token ... "
       f"--result-file {result_path}")

def assert_visible(lwar_id, role, opened_path) -> None:
    if not path_allowed(VISIBLE[role], lwar_id, opened_path):
        raise ProtocolError("visibility jail")
    # acceptance_criteria:
    #   - begin 없이 dispatch 금지
    #   - complete 플래그는 --result-file. --artifacts 없음
    #   - 금지 경로 읽기 = protocol_error, 시드 무효
```

### IfGenerate

```python
MVP_UNKNOWN = {"known_unknown", "contradictory"}
NEGATION_CUES = ("아니", "않다", "반대", "모순", "불가능", "not", "cannot", "contradict")

def extract_claim_lines(hint_files: list[str]) -> list[dict]:
    """불릿/문장 분할. claim_id = H-{file}-{i}."""
    ...

def contradictory_pairs(claims: list[dict]) -> list[tuple]:
    """한쪽만 NEGATION_CUES 를 가진 근사 중복 쌍."""
    ...

def make_u(run_id: str, n: int, typ: str, claim: dict, extra=None) -> dict:
    ids = [claim["claim_id"]] + ([extra["claim_id"]] if extra else [])
    return {"id": f"U-{run_id}-{n}", "unknown_type": typ,
            "statement": claim["text"], "claim_ids": ids,
            "source_hint": claim.get("source")}

def mine_min(hint_files: list[str], run_id: str) -> list[dict]:
    """결정론. LLM이 unknown을 발명하지 않는다. MVP 2종만."""
    claims = extract_claim_lines(hint_files)
    out, n = [], 0
    for c in claims:
        if not c.get("source"):
            n += 1
            out.append(make_u(run_id, n, "known_unknown", c))
    for a, b in contradictory_pairs(claims):
        n += 1
        out.append(make_u(run_id, n, "contradictory", a, extra=b))
    return [u for u in out if u["claim_ids"] and u["unknown_type"] in MVP_UNKNOWN]

def generate(inbox: dict) -> list:
    sl = inbox["allocation_slice"]
    hints = list_files("hints/")                 # jail 상대
    unknowns = mine_min(hints, inbox["run_id"])
    if not unknowns:
        return []
    seeds, seq = [], 0
    for u in unknowns:
        for op in sl["operators"]:
            raw = AI_apply_operator(u, op, objective=sl["objective"],
                                    avoid=sl["avoid_patterns"],
                                    must_consider=sl.get("must_consider") or [])
            if raw is None or not raw.get("evidence"):
                continue
            seq += 1
            seed = fill_seed(f"{current_lwar()}-{seq:02d}", raw, u, op, sl, inbox)
            seed["question_norm"] = normalize_tokens(seed["question"])
            if not mechanical_ok_shape(seed, sl.get("hint_strings") or []):
                continue
            if seed["question_class"] in {"normative", "meta"}:
                continue
            seeds.append(seed)
            if len(seeds) >= sl["max_seeds"]:
                return seeds
    return seeds

def normalize_tokens(text: str) -> str:
    """NFC, 소문자, 기호→공백, 한글은 2글자 슬라이스, 그 외 whitespace split."""
    ...

def mechanical_ok_shape(seed: dict, hints: list[str]) -> bool:
    g = mechanical_gates(seed, hints)
    return all(g[k] == "pass" for k in MECH)

def fill_seed(local_id, raw, u, op, sl, inbox) -> dict:
    return {
        "local_id": local_id,
        "question_id": None,
        "question": raw["question"],
        "question_norm": "",
        "question_class": raw["question_class"],
        "operator": op,
        "unknown_type": u["unknown_type"],
        "unknown_ref": u["id"],
        "target_concepts": raw.get("target_concepts") or [],
        "why_matters": raw.get("why_matters") or "",
        "assumptions": raw.get("assumptions") or [],
        "unknowns": raw.get("unknowns") or [u["statement"]],
        "evidence": raw["evidence"],            # 없으면 generate 가 drop
        "falsifier": raw.get("falsifier") or "",
        "minimal_test": raw.get("minimal_test") or {},
        "action_plan": raw.get("action_plan") or {},
        "lineage": {
            "generated_by": current_lwar(),
            "evidence_kind": sl["evidence_kind"],
            "objective": sl["objective"],
            "run_id": inbox["run_id"],
            "parents": [],
            "domain": inbox["domain"],
        },
    }
    # acceptance_criteria:
    #   - question_id 가 채워진 seed 0 (워커)
    #   - unknown_ref 없는 seed 0
    #   - evidence 날조 경로 없음
    #   - MVP 타입이 known_unknown|contradictory 외면 무효
```

### IfContrarian

```python
def evidence_broken(q: dict) -> bool:
    return (not q.get("evidence")
            or any(e.get("claim") == q.get("unknowns", [None])[0] for e in q["evidence"]))

def premise_forbidden(q: dict, forbidden: list[str]) -> bool:
    blob = " ".join(q.get("assumptions") or [])
    return any(p and p in blob for p in forbidden)

KILL_RULES = {
    "evidence":  lambda q, atk, fb: evidence_broken(q),
    "premise":   lambda q, atk, fb: premise_forbidden(q, fb),
}

def cross_examine(inbox: dict) -> list:
    forbidden = inbox.get("forbidden_premises") or []
    reports = []
    for q in inbox["questions"]:
        if q.get("lineage", {}).get("generated_by") == current_lwar():
            raise ProtocolError("self-examine")
        attacks = []
        for dtype in ["evidence", "logic", "premise",
                      "alternative", "stakeholder", "execution"]:
            atk = AI_generate_attack(q, dtype)
            if dtype in KILL_RULES and KILL_RULES[dtype](q, atk, forbidden):
                res, rule = "kill", dtype
            else:
                res, rule = "wound" if AI_is_material(q, atk) else "miss", None
            attacks.append({"dtype": dtype, "attack": atk["text"],
                            "result": res, "rationale": atk["why"],
                            "kill_rule": rule})
        kills = sum(1 for a in attacks if a["result"] == "kill")
        reports.append({
            "local_id": q["local_id"], "examiner": current_lwar(),
            "attacks": attacks, "kill_count": kills,
            "verdict": "KILLED" if kills >= 1 else "SURVIVED",
        })
    return reports
    # acceptance_criteria:
    #   - 6유형 전부
    #   - AI 가 verdict 문자열을 직접 쓰지 않음
    #   - AI 가 kill 을 직접 부여하지 않음 (규칙만)
    #   - D19: kills >= 1 → KILLED
    #   - inbox.forbidden_premises 필수 키 (빈 리스트 허용)
```

### IfJudge

```python
def blind_packet(q: dict, anon_id: str) -> dict:
    """OA가 judge inbox를 만들 때 호출. 워커는 원본을 못 본다."""
    return {
        "anon_id": anon_id,
        "question": template_restyle(q),     # 개념-전제-미지-반증 템플릿 (결정론)
        "question_class": q["question_class"],
        "unknown_type": q["unknown_type"],
        "target_concepts": q["target_concepts"],
        "assumptions": q["assumptions"],
        "unknowns": q["unknowns"],
        "evidence_claims": [e["claim"] for e in q["evidence"]],  # source 제거
        "minimal_test": q["minimal_test"],
        "action_plan": q["action_plan"],
    }
    # local_id, question_id, operator, generated_by 미포함

def template_restyle(q: dict) -> str:
    """결정론 4줄: concept / premise / unknown / falsifier."""
    return "\n".join([
        "concept: " + ", ".join(q.get("target_concepts") or []),
        "premise: " + "; ".join(q.get("assumptions") or []),
        "unknown: " + "; ".join(q.get("unknowns") or []),
        "falsifier: " + (q.get("falsifier") or ""),
    ])

def judge(inbox: dict) -> list:
    cards = []
    hints_placeholder = ["*"]                 # source 매칭은 Compose가 원본으로 재실행
    for b in inbox["questions"]:
        # mechanical_gates on blinded packet: CLEAR/PATH/TESTSHAPE only
        shape = {
            "target_concepts": b.get("target_concepts"),
            "assumptions": b.get("assumptions"),
            "unknowns": b.get("unknowns"),
            "action_plan": b.get("action_plan"),
            "minimal_test": b.get("minimal_test"),
            "evidence": [{"source": "hidden", "claim": c} for c in b.get("evidence_claims", [])],
        }
        gates = mechanical_gates(shape, ["hidden"])
        # G-GROUND source 매칭은 블라인드에서 건너뛰고 Compose가 원본으로 확정
        if any(gates[g] == "fail" for g in ("G-CLEAR", "G-PATH", "G-TESTSHAPE")):
            cards.append({"anon_id": b["anon_id"], "verdict": "GATE_FAIL",
                          "failed_gate": first_fail(gates), "scores": {}, "notes": ""})
            continue
        cards.append({
            "anon_id": b["anon_id"],
            "verdict": "SCORED",
            "failed_gate": None,
            "scores": {
                "impact": AI_assess_impact_rubric(b, axes=["stakeholders", "cost_bound"]),
                "testability": AI_assess_testability(b),
                "grounding": min(1.0, len(b.get("evidence_claims", [])) / 3),
                "actionability": 1.0 if distinct_content(b["action_plan"]) else 0.0,
            },
            "notes": "",
        })
    extra = set(flatten_keys(cards)) & {"novelty", "diversity_contribution", "question_id"}
    if extra:
        raise ProtocolError("forbidden score keys")
    return cards
    # acceptance_criteria:
    #   - inbox/outbox 에 question_id, local_id, operator, generated_by, source URL 없음
    #   - scores 키 ⊆ {impact, testability, grounding, actionability}
```

### IfPhase2Roles

```python
def phase2_roles_blocked() -> str:
    return (
        "if-unknown-miner: 10분류 + claim-graph 단절. "
        "if-novelty: 코퍼스+web, 검색0건 재질의, 자동 NOVEL 금지. "
        "if-action: G-ACTION 기계화. "
        "if-safety: HIGH -> QUARANTINE."
    )
    # blocker: HumanClose 가 awaiting_human 까지 도달하지 않음
    # seam: IfRole 테이블 + inbox 스키마 확장. IfJudge 점수축을 열지 않음
```

### Allocate

```python
FAMILY_NORM = {"claude": "anthropic", "anthropic": "anthropic",
               "gpt": "openai", "openai": "openai",
               "gemini": "google", "grok": "xai", "deepseek": "deepseek"}

def vendor_family(lwar: dict) -> str:
    raw = lwar.get("vendor_family") or (lwar.get("profile") or {}).get("vendor_family")
    if not raw:
        raise Blocked(f"{lwar.get('lwar_id')} missing vendor_family")
    return FAMILY_NORM.get(raw.lower(), raw.lower())

def build_allocation(brief: dict, lwars: list) -> dict:
    families = {vendor_family(x) for x in lwars}
    if brief.get("mode", "normal") == "normal" and len(families) < 2:
        raise Blocked("need >= 2 vendor_family for normal mode")
    kinds = list(brief.get("evidence_hints") or {}) or list(EvidenceKind.__args__)
    objs = ["importance_max", "consensus_falsify", "info_per_cost"]
    avoid_all = query_avoid_patterns(brief["domain"])
    table, used = {}, set()
    for i, lwar in enumerate(lwars):
        fam = vendor_family(lwar)
        ev = kinds[i % len(kinds)]
        ops = default_ops_for(i, 3)
        key = (fam, frozenset(ops), ev)
        if key in used:
            ops = leftover_ops(used, fam, ev, ops)
            if ops is None:
                ev = kinds[(i + 1) % len(kinds)]
                ops = leftover_ops(used, fam, ev, default_ops_for(i + 7, 3))
            if ops is None:
                raise Blocked("cannot satisfy heterogeneity key")
            key = (fam, frozenset(ops), ev)
        used.add(key)
        slice_avoid = avoid_all[i::len(lwars)]     # 동일 목록 공유 금지
        table[lwar["lwar_id"]] = {
            "vendor_family": fam,
            "operators": ops,
            "evidence_kind": ev,
            "objective": objs[i % 3],
            "avoid_patterns": slice_avoid,
            "hint_strings": (brief.get("evidence_hints") or {}).get(ev, []),
            "max_seeds": brief["budget"]["max_seeds_per_lwar"],
            "must_consider": (brief.get("must_consider_slices") or {}).get(lwar["lwar_id"], []),
        }
    return table
    # acceptance_criteria:
    #   - 동일 vendor_family 에 동일 (ops-set, evidence_kind) 0
    #   - 기본 경로에 AI_select_operators 없음
    #   - avoid_patterns 전 LWAR 동일 배열 금지
```

### ExploreLoop

```python
def token_set(seed: dict) -> set:
    """question_norm 만. target_concepts 는 AI 가 채우므로 Jaccard 에 넣지 않음."""
    return set((seed.get("question_norm") or "").split())

def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)

def load_status(*st) -> list:
    return [load(p) for p in iter_questions() if load(p).get("status") in st]

def prior_sets_for(domain: str, n: int = 50) -> list:
    qs = [q for q in load_status("SCORED", "ADOPTED")
          if q.get("lineage", {}).get("domain") == domain]
    return [token_set(q) for q in qs[-n:]]

def diversity_ok(seeds, prior_sets, th_mean=0.40, th_pair=0.55) -> bool:
    """D20: th_pair = 런 내부 쌍만. prior 는 mean 에만."""
    if len(seeds) < 2:
        return False                         # 호출자가 empty vs diversity 를 분기
    sets = [token_set(s) for s in seeds]
    pairs = [jaccard(sets[i], sets[j]) for i in range(len(sets)) for j in range(i+1, len(sets))]
    if max(pairs) > th_pair:
        return False
    prior = [jaccard(token_set(s), p) for s in seeds for p in prior_sets]
    pool = pairs + prior
    return (sum(pool) / len(pool)) <= th_mean

def rotate_kind(ev: str) -> str:
    kinds = list(EvidenceKind.__args__)
    return kinds[(kinds.index(ev) + 1) % len(kinds)] if ev in kinds else kinds[0]

def inject_divergence(alloc: dict, brief: dict) -> dict:
    nxt = {k: dict(v) for k, v in alloc.items()}
    used_ops = {op for sl in nxt.values() for op in sl["operators"]}
    unused = [op for op, _ in OPERATORS if op not in used_ops] or [op for op, _ in OPERATORS]
    keys = set()
    for i, sl in enumerate(nxt.values()):
        new_ops = sl["operators"][:]
        new_ops[i % len(new_ops)] = unused[i % len(unused)]
        if not (2 <= len(set(new_ops)) <= 3):
            new_ops = default_ops_for(i + 3, 3)
        sl["operators"] = new_ops
        sl["evidence_kind"] = rotate_kind(sl["evidence_kind"])
        sl["hint_strings"] = (brief.get("evidence_hints") or {}).get(sl["evidence_kind"], [])
        key = (sl["vendor_family"], frozenset(sl["operators"]), sl["evidence_kind"])
        if key in keys:
            raise Blocked("divergence broke heterogeneity")
        keys.add(key)
    return nxt

def explore_loop(run, alloc, lwars, brief) -> list:
    prior = prior_sets_for(brief["domain"], 50)
    seeds, rounds = [], 0
    while rounds < brief["budget"]["max_rounds"]:
        items = [(lid, make_generate_inbox(run, lid, sl)) for lid, sl in alloc.items()]
        got, st = publish_collect(run, "generate", items, lwars, timeout_s=900)
        run.observed_statuses.extend(st)
        seeds = flatten_seeds(got, run.id)
        if diversity_ok(seeds, prior):
            return seeds
        if rounds == brief["budget"]["max_rounds"] - 1:
            if len(seeds) < 2:
                return seeds                 # IfCycle → empty_unknowns_or_seeds
            raise Blocked("diversity_failed")
        alloc = inject_divergence(alloc, brief)
        write_yaml(run / "allocation.yaml", alloc)
        materialize_hints(run, alloc, brief)
        rounds += 1
    return seeds
    # acceptance_criteria:
    #   - 마지막 라운드 강제 수용 없음
    #   - seed < 2 는 diversity_failed 가 아님
    #   - divergence 후 (jail hints, hint_strings, evidence_kind) 3자 일치
    #   - EXPLORE inbox 에 타 시드 0
```

### ExploitLoop

```python
def seed_key(s: dict) -> str:
    return s["local_id"]

def cross_assign(seeds, lwars, *, forbid_ids: dict[str, set]) -> dict:
    """각 seed를 forbid에 없는 LWAR에 라운드로빈. 실패면 Blocked."""
    assign, i = {}, 0
    ids = [w["lwar_id"] for w in lwars]
    for s in seeds:
        banned = forbid_ids.get(seed_key(s), set())
        tried = 0
        while ids[i % len(ids)] in banned:
            i += 1
            tried += 1
            if tried > len(ids):
                raise Blocked(f"no examiner for {seed_key(s)}")
        assign.setdefault(ids[i % len(ids)], []).append(s)
        i += 1
    return assign

def mint_anon(run_nonce: bytes, local_id: str) -> str:
    """워커는 run_nonce 를 보지 못함. unsalted sha256(local_id) 금지."""
    return "A-" + hmac_sha256(run_nonce, local_id.encode()).hex()[:12]

def rekey(cards_raw: dict, anon_map: dict) -> dict:
    """judge outbox {anon_id: card} → {local_id: card+ids}. 미지/중복 anon 은 omit."""
    out = {}
    seen = set()
    for batch in cards_raw.values() if isinstance(cards_raw, dict) else cards_raw:
        for card in (batch if isinstance(batch, list) else [batch]):
            aid = card.get("anon_id")
            if not aid or aid not in anon_map or aid in seen:
                continue
            seen.add(aid)
            local_id = anon_map[aid]
            out[local_id] = {**card, "local_id": local_id}
    return out

def exploit_loop(run, seeds, lwars, mode: RunMode, brief) -> tuple:
    if mode == "normal" and len(lwars) < 3:
        raise Blocked("normal mode needs 3 LWARs")
    c_forb = {seed_key(s): {s["lineage"]["generated_by"]} for s in seeds}
    c_asg = cross_assign(seeds, lwars, forbid_ids=c_forb)
    c_items = [(lid, {"role": "contrarian", "questions": qs,
                      "forbidden_premises": brief.get("forbidden_premises") or []})
               for lid, qs in c_asg.items()]
    raw_d, st = publish_collect(run, "contrarian", c_items, lwars, 600)
    run.observed_statuses.extend(st)
    dissents = index_by_local(raw_d)
    j_forb = {seed_key(s): {s["lineage"]["generated_by"]} for s in seeds}
    if mode == "normal":
        for s in seeds:
            d = dissents.get(seed_key(s))
            if d:
                j_forb[seed_key(s)].add(d["examiner"])
    j_asg = cross_assign(seeds, lwars, forbid_ids=j_forb)
    packets, anon_map = [], {}
    for lwar, qs in j_asg.items():
        blinded, excl = [], set()
        for q in qs:
            aid = mint_anon(run.nonce, q["local_id"])
            anon_map[aid] = q["local_id"]
            blinded.append(blind_packet(q, aid))
            excl |= j_forb[seed_key(q)]
        packets.append((lwar, {"role": "judge", "questions": blinded,
                               "exclude_lwars": list(excl)}))
    cards_raw, st = publish_collect(run, "judge", packets, lwars, 600)
    run.observed_statuses.extend(st)
    cards = rekey(cards_raw, anon_map)
    if mode == "normal":
        missing = [s["local_id"] for s in seeds if s["local_id"] not in dissents]
        if missing:
            raise Blocked("protocol_incomplete")
    return dissents, cards
    # acceptance_criteria:
    #   - normal: generated_by, examiner, judge 가 질문마다 서로 다름
    #   - normal: dissent 누락 → Blocked(protocol_incomplete). empty_dissent 금지
    #   - ablation: judge != generated_by 만. empty_dissent 허용
    #   - judge inbox 에 원본 question_id 없음
    #   - anon_id 는 run_nonce HMAC. 워커 정보만으로 local_id 복원 불가
```

### Compose

```python
def empty_dissent(s: dict) -> dict:
    """ablation only. normal 은 exploit_loop 가 Blocked."""
    return {"local_id": s["local_id"], "examiner": None, "attacks": [],
            "kill_count": 0, "verdict": "SURVIVED"}

def stamp_lineage(seed: dict, src_lwar: str, run_id: str) -> dict:
    claimed = seed.get("lineage", {}).get("generated_by")
    if claimed not in {None, src_lwar}:
        raise Drop("forged generated_by")
    seed.setdefault("lineage", {})
    seed["lineage"]["generated_by"] = src_lwar
    seed["lineage"]["run_id"] = run_id
    return seed

def materialize_qo(seed, dissent, card, qid, hints, now_ts) -> dict:
    q = dict(seed)
    q.update({
        "question_id": qid,
        "status": "DRAFT",
        "contradictions": seed.get("contradictions") or [],
        "estimated_cost": seed.get("estimated_cost") or "",
        "created_at": now_ts,
        "last_verified_at": now_ts,
        "dissent": [a for a in dissent.get("attacks", []) if a["result"] != "miss"],
        "gate_results": mechanical_gates(seed, hints),
        "human_review": {"status": "pending", "reviewer": "", "note": ""},
        "scores": {},
    })
    return q

def compose(run, seeds, dissents, cards, hints_by_kind, mode: RunMode) -> list:
    out = []
    ts = now()
    for s in seeds:
        d = dissents.get(s["local_id"])
        if d is None:
            if mode == "normal":
                raise Blocked("protocol_incomplete")
            d = empty_dissent(s)
        c = cards.get(s["local_id"]) or {"verdict": "GATE_FAIL", "scores": {},
                                         "failed_gate": "missing_card"}
        qid = reuse_or_mint(run, s["local_id"], run.id)
        hints = hints_by_kind.get(s["lineage"]["evidence_kind"], [])
        q = materialize_qo(s, d, c, qid, hints, ts)
        mech_fail = any(q["gate_results"][g] == "fail" for g in MECH)
        if d.get("verdict") == "KILLED" or c.get("verdict") == "GATE_FAIL" or mech_fail:
            nxt = "REJECTED"
        elif q["question_class"] in {"normative", "meta"}:
            nxt = "DORMANT"
        else:
            q["scores"] = c.get("scores") or {}
            nxt = "SCORED"
        write_question(q, actor="oa")
        q["status"] = nxt
        write_question(q, actor="oa")
        d["question_id"] = qid
        d["run_id"] = run.id
        append_jsonl("$IF_ROOT/dissent/dissent_log.jsonl", d)
        out.append(q)
    return out
    # acceptance_criteria:
    #   - first write DRAFT 가 validate(q) 통과 (필수 필드 전부)
    #   - compose 재실행 mint 0 (local_id_map)
    #   - len(out) == len(seeds)
    #   - ADOPTED 0
```

### HumanClose

```python
def pareto(qos, axes, k=12) -> list:
    cand = sorted([q for q in qos if q["status"] == "SCORED"],
                  key=lambda q: q["question_id"])
    return nondominated(cand, axes)[:k]

def open_review(run, qos) -> dict:
    scored = [q for q in qos if q["status"] == "SCORED"]
    portfolio = pareto(qos, ["testability", "actionability", "grounding"], 12)
    dissent_p = [q for q in qos
                 if q["status"] in {"REJECTED", "SCORED", "DORMANT"}
                 and any(a["result"] in {"wound", "kill"} for a in q.get("dissent", []))]
    mech_rej = [q for q in qos if q["status"] == "REJECTED"]
    cards = []
    for q in unique(portfolio + dissent_p + mech_rej):
        info = q["status"] == "REJECTED" and q not in portfolio
        cards.append({
            "question_id": q["question_id"],
            "question": q["question"],
            "minimal_test": q["minimal_test"],
            "decision": "reject" if info else "pending",
            "reason": "mechanical_rejected" if info else "",
            "informational": info,                 # D21
            "checks": {"already_answered": None, "test_runnable": None, "duplicate": None},
            "bucket": "informational" if info else (
                "dissent" if q in dissent_p and q not in portfolio else "pareto"),
        })
    doc = {"run_id": run.id, "reviewer": "",
           "portfolio": [q["question_id"] for q in portfolio],
           "all_scored": [q["question_id"] for q in scored],
           "dissent_portfolio": [q["question_id"] for q in dissent_p],
           "decisions": cards}
    write_yaml(run / "review.yaml", doc)
    return {"status": "awaiting_human", "dissent_referenced": True}

def preflight_close(doc, report) -> None:
    """write 0회. 실패 시 디스크 불변."""
    if not doc.get("reviewer"):
        raise Blocked("reviewer required")
    if report.get("mode") == "ablation" and any(
        d.get("decision") == "adopt" and not d.get("informational")
        for d in doc["decisions"]
    ):
        raise Blocked("ablation cannot ADOPT")
    for d in doc["decisions"]:
        if d.get("informational"):
            continue
        if d["decision"] == "pending" or not d.get("reason"):
            raise Blocked("pending or empty reason")
        if d["decision"] == "adopt" and d.get("informational"):
            raise Blocked("informational cannot ADOPT")
    logged = [x for x in load_jsonl("$IF_ROOT/dissent/dissent_log.jsonl")
              if x.get("run_id") == doc["run_id"]]
    wounded_ids = {x["question_id"] for x in logged
                   if x.get("question_id") and (
                       x.get("kill_count", 0) > 0
                       or any(a.get("result") in {"wound", "kill"}
                              for a in x.get("attacks") or []))}
    listed = set(doc.get("dissent_portfolio") or [])
    if wounded_ids and not wounded_ids <= listed:
        raise Blocked("dissent_not_referenced")

def close_review(run) -> dict:
    """if_cycle close. preflight 후 mutation. REVIEWED 는 재적용."""
    doc = read_yaml(run / "review.yaml")
    report = load_report(run)
    preflight_close(doc, report)
    decided = {"adopt": 0, "reject": 0, "defer": 0}
    for d in doc["decisions"]:
        if d.get("informational"):
            record_decision({**d, "domain": load(d["question_id"])["lineage"]["domain"],
                             "run_id": doc["run_id"], "ts": now()})
            decided["reject"] += 1
            continue
        q = load(d["question_id"])
        if q["status"] in {"ADOPTED", "REJECTED", "DEFERRED"}:
            continue
        if q["status"] != "REVIEWED":
            q["status"] = "REVIEWED"
            write_question(q, actor="human", reviewer_ok=True)
        final = {"adopt": "ADOPTED", "reject": "REJECTED",
                 "defer": "DEFERRED"}[d["decision"]]
        q["status"] = final
        q["human_review"] = {"status": d["decision"], "reviewer": doc["reviewer"],
                             "note": d["reason"]}
        write_question(q, actor="human", reviewer_ok=True)
        record_decision({**d, "domain": q["lineage"]["domain"],
                         "run_id": doc["run_id"], "ts": now()})
        decided[d["decision"]] += 1
    report["human"] = "closed"
    report["dissent_referenced"] = True
    report["decided"] = decided
    write_yaml(run / "report.yaml", report)
    return {"status": "closed", "dissent_referenced": True, "decided": decided}
    # acceptance_criteria:
    #   - write 전 preflight. V15 ablation+adopt → mutation 0
    #   - REVIEWED 중간 저장 후 재개 → final 1회 (V11)
    #   - informational 카드 adopt 불가, record_decision 은 수행
    #   - DORMANT wound 는 dissent_portfolio 로 close 가능 (V13)
    #   - review.yaml 에 scores, generated_by 없음
```

### IfCycle

```python
# entry: python .agents/skills/if-core/scripts/if_cycle.py run --brief PATH
#        python .agents/skills/if-core/scripts/if_cycle.py close --run RUN-ID
# 이 프로세스가 PAO_OA_ID 를 들고 IfOa 래퍼로 send/collect 한다.

def load_ready_lwars() -> list:
    """PAO registry on + fresh heartbeat + vendor_family 필수."""
    ...

def init_run(brief: dict):
    """$IF_ROOT/runs/{brief_id}/ 생성. 기존 디렉토리 있으면 거절. nonce 기록."""
    ...

def materialize_hints(run, alloc, brief) -> None:
    """ensure_jail + hints 슬라이스 복사. allocation.yaml 은 jail 밖."""
    ...

def make_generate_inbox(run, lwar_id, sl) -> dict:
    """run_id, domain, allocation_slice. 타 시드 0."""
    return {"role": "generate", "run_id": run.id, "domain": run.brief["domain"],
            "allocation_slice": sl}

def flatten_seeds(accepted: dict, run_id: str) -> list:
    """lwar_id → outbox list[seed]. stamp_lineage 후 합친다. 위조는 drop."""
    out = []
    for lid, box in accepted.items():
        for s in box if isinstance(box, list) else []:
            try:
                out.append(stamp_lineage(s, lid, run_id))
            except Drop:
                continue
    return out

def compute_protocol_valid(obs) -> bool:
    return all([
        obs["mode"] == "normal",
        obs["n_lwars"] >= 3,
        obs["contributing_generate_lwars"] >= 3,
        obs["protocol_error_count"] == 0,
        obs["seed_count"] > 0 and obs["qo_count"] == obs["seed_count"],
        obs["all_unknown_ref"],
        obs["dissent_coverage"],
        obs["vendor_families"] >= 2,
    ])

def inquiry_cycle(brief_raw: dict) -> dict:
    brief = normalize_brief(brief_raw)
    if not (brief.get("evidence_hints") or {}):
        raise Blocked("evidence_hints empty")
    lwars = load_ready_lwars()
    mode = brief.get("mode", "normal")
    if mode == "normal" and len(lwars) < 3:
        raise Blocked("normal mode needs >= 3 LWARs")
    if len(lwars) < 2:
        raise Blocked("need >= 2 LWARs")
    run = init_run(brief)
    run.observed_statuses = []
    alloc = build_allocation(brief, lwars)
    write_yaml(run / "allocation.yaml", alloc)
    materialize_hints(run, alloc, brief)
    seeds = explore_loop(run, alloc, lwars, brief)
    if not seeds:
        return fail_report(run, "empty_unknowns_or_seeds")
    dissents, cards = exploit_loop(run, seeds, lwars, mode, brief)
    qos = compose(run, seeds, dissents, cards, brief.get("evidence_hints") or {}, mode)
    human = open_review(run, qos)
    scored = [q for q in qos if q["status"] == "SCORED"]
    contrib = {s["lineage"]["generated_by"] for s in seeds}
    valid = compute_protocol_valid({
        "mode": mode, "n_lwars": len(lwars),
        "contributing_generate_lwars": len(contrib),
        "protocol_error_count": run.observed_statuses.count("protocol_error"),
        "seed_count": len(seeds), "qo_count": len(qos),
        "all_unknown_ref": all(s.get("unknown_ref") for s in seeds),
        "dissent_coverage": mode != "normal" or len(dissents) == len(seeds),
        "vendor_families": len({vendor_family(w) for w in lwars}),
    })
    report = {
        "run_id": run.id, "mode": mode,
        "separation": "full" if mode == "normal" else "ablation",
        "protocol_valid": valid,
        "hypothesis_valid": valid,
        "seed_count": len(seeds), "qo_count": len(qos),
        "scored_count": len(scored),
        "human": human["status"],
        "dissent_referenced": human.get("dissent_referenced", True),
        "slo_scored_ge_8": len(scored) >= 8,
        "contributing_generate_lwars": len(contrib),
        "observed_statuses": run.observed_statuses,
    }
    write_yaml(run / "report.yaml", report)
    return report
    # acceptance_criteria (build gate, not SLO):
    #   - qo_count == seed_count and seed_count > 0
    #   - provenance 공란 0
    #   - dissent_log 라인 수 == seed_count
    #   - protocol_valid 상수 True 금지
    #   - empty 탐사지 = empty_unknowns_or_seeds (not diversity_failed)
    # SLO: scored_count >= 8
```

---

## Deterministic / AI boundary

| Deterministic | `AI_` |
|---|---|
| 스키마, id lock, I/O, 전이, edges | operator 적용 |
| mine_min, Jaccard, 게이트, source↔hint 매칭 | 반론 문장 생성, wound/miss |
| kill 규칙, verdict from kill_count | impact 루브릭, testability |
| Pareto(결정론 축), blind_packet, HMAC anon, PAO send/collect 폴링 | |
| avoid_patterns 원문 n개, default_ops_for | |

---

## Visibility reject tests

구현 전 고정할 거부 테스트. 통과하지 못하면 불변식이 문장일 뿐이다.

| ID | Act | Expected |
|---|---|---|
| V1 | generate가 `runs/*/outbox/*` 또는 `allocation.yaml`을 연다 | `protocol_error` |
| V2 | judge inbox에 `question_id` 또는 `generated_by`가 있다 | 발행 거부 |
| V3 | `write_question(..., actor="oa")`로 `ADOPTED` | 거절 |
| V4 | ScoreCard에 `novelty` | 카드 폐기 |
| V5 | normal 런, LWAR=2 | `Blocked` |
| V6 | ablation 런에서 adopt | `Blocked` |
| V7 | `close_review` reviewer 공란 | `Blocked` |
| V8 | 다양성 실패 후 강제 EXPLOIT | 금지, `Blocked("diversity_failed")` |
| V9 | IfGenerate가 `alloc_question_id` 또는 `graph/`를 연다 | `protocol_error` |
| V10 | judge outbox에 `question_id` | 스키마 실패, complete 거절 |
| V11 | REVIEWED에서 close 재실행 | final 1회, 중복 decision 0 |
| V12 | generated_by 위조 시드 | 수집 drop |
| V13 | DORMANT+wound 런 close | incomplete 아님 |
| V14 | 빈 탐사지 | `empty_unknowns_or_seeds`, not `diversity_failed` |
| V15 | ablation+adopt | preflight reject, QO 불변 |
| V16 | contrarian outbox에 `question_id` | 스키마 실패 |
| V17 | divergence 후 G-GROUND 전원 fail | 회귀 금지 (hints 3자 일치) |
| V18 | unsalted `sha256(local_id)` anon | 발행 거부 |

---

## Implementation order (not a WORKPLAN)

```
M1 SchemaPack + GatePack + StatePack + validate.py + V-tests as fixtures
M2 StoreIo (lock, first-write DRAFT, edges optional rel)
M3 BusContract + IfOa/IfLwar overlay (poll collect, begin/complete)
M4 Allocate + IfGenerate/IfContrarian/IfJudge
M5 IfCycle E2E fixture 그리고 별도 라이브 런 (LWAR>=3)
M6 IfPhase2Roles   # blocked until M5 awaiting_human
```

---

## Design completion

- [x] Gantree depth ≤ 5, 자식 < 10, 상태·의존 명시, 노드 22
- [x] 복합 노드 PPR + acceptance_criteria
- [x] PAO 실제 스키마와 모순 없음
- [x] design-review cycle 1 반영
- [x] design-review cycle 2 반영
- [x] design-review cycle 3 / D19–D21 / Wave1 fail-closed 반영
- [x] `/PGF plan` — `.pgf/WORKPLAN-InquiryFoundry.md`
