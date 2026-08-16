# InquiryFoundry — 시스템 설계서

**Version** 0.1 (Draft) · **Status** designing · **Notation** PG v1.3 (Gantree + PPR) · **Target Runtime** Claude Code CLI + 이종 CLI LWAR군
**Dependencies** PAO (pao-oa / pao-lwar 런타임), PG/PGF 스킬, HELIX explore/exploit 개념

---

## 1. 목적과 범위

InquiryFoundry(IF)는 다종 AI 에이전트가 서로 다른 지식·관점·반론을 교차시켜 **검증 가능하고 행동 가능한 새로운 질문(Question Object)** 을 생산하는 Inquiry Intelligence System이다.

본 설계서는 IF를 **에이전트가 실행하는 스킬 묶음**으로 구현하기 위한 명세다. 설치 방식은 PAO와 동일한 **폴더 복사(self-contained)** 를 전제로 하며, Claude Code CLI에서 본 문서를 읽고 단계적으로 구체화하는 것을 목표로 한다.

### 1.1 설계 확정 원칙 (전 스킬 공통 계약)

1. **Independent First, Interact Later** — 독립 생성 완료 전 에이전트 간 컨텍스트 공유 금지.
2. **스킬 = 역할, 세션 = 모델** — 이종성(heterogeneity)은 스킬이 아니라 런타임(LWAR) 배분에서 나온다. OA가 operator/evidence pack/objective를 배분해 4차원 이종성을 강제한다.
3. **생성·심사 분리** — 생성에 참여한 (lwar_id, task_id) 조합은 동일 배치의 심사에 참여 금지.
4. **외부 그라운딩 novelty** — LLM 자체 novelty 판단 금지. 반드시 외부 검색·기존 질문 코퍼스 대조.
5. **Actionability Gate** — 최소 실행계획 생성에 실패한 질문은 기각.
6. **Dissent Preservation** — 합의는 종료조건이 아니다. 불일치는 제거하지 않고 새 질문의 원료로 보존.
7. **Human Gate** — 질문의 최종 채택(ADOPTED)은 인간 승인 없이 불가.
8. **Provenance 전수 기록** — 모든 질문은 계보(생성 LWAR, operator, evidence, 반론, 판정)를 가진다.

### 1.2 비범위 (v0.1)

- 실험 자동 실행(Experiment Runner) — Phase 3 이후
- 분산 다중 호스트 버스 — 단일 `IF_ROOT` 파일 버스만
- 평가 가중치 자동 학습 — 채택 로그 축적 후 별도 설계

---

## 2. 시스템 구조 개요

### 2.1 전체 Gantree

```
InquiryFoundry // 질문 생산 시스템 (designing) @v:0.1
    Layer0_Foundation // 공용 기반 (designing)
        IfCore // 스키마·연산자·게이트·상태머신 정의 (designing)
        IfGraph // Question Graph 저장·질의 (designing) @dep:IfCore
        IfMemory // 채택/기각 이력·실패 패턴 (designing) @dep:IfCore
    Layer1_Orchestration // 오케스트레이션 (designing) @dep:Layer0_Foundation
        IfOa // OA 확장: 파이프라인 구동·발산수렴 제어 (designing)
        IfLwar // LWAR 확장: 프로파일 신고·역할 스킬 로드 (designing)
    Layer2_RoleSkills // 역할 스킬 8종 (designing) @dep:Layer1_Orchestration
        IfUnknownMiner // 미지 탐지 (designing)
        IfQuestionGen // 독립 발산 생성 (designing)
        IfContrarian // 구조화 반론 (designing)
        IfNoveltyChecker // 외부 그라운딩 신규성 검증 (designing)
        IfActionability // 실행 게이트 (designing)
        IfJudge // 블라인드 평가 (designing)
        IfComposer // Question Object 조립·그래프 등록 (designing)
        IfSafety // 안전 점검 (designing)
    Layer3_Pipeline // 파이프라인 정의 (designing) @dep:Layer2_RoleSkills
        InquiryRun // 1회 탐구 사이클 실행 정의 (designing)
        HumanReview // 인간 승인 관문 (designing)
        FeedbackLoop // 결과 재반영 (designing)
```

### 2.2 디렉터리 구조 (설치 형태)

PAO 방식과 동일: 스킬 폴더 복사만으로 설치, 환경변수는 `IF_ROOT` 하나만 사용. `IF_ROOT`는 PAO 버스(`PAO_ROOT`)와 별도의 IF 데이터 루트다.

```text
skills/
    if-core/            # SKILL.md + schemas/ + operators/ + gates/
    if-graph/           # SKILL.md + scripts/graph_io.py
    if-memory/          # SKILL.md + scripts/memory_io.py
    if-oa/              # SKILL.md + scripts/ (pao-oa 런타임 동봉 + IF 확장)
    if-lwar/            # SKILL.md + scripts/ (pao-lwar 런타임 동봉 + IF 확장)
    if-unknown-miner/   # SKILL.md
    if-question-gen/    # SKILL.md
    if-contrarian/      # SKILL.md
    if-novelty-checker/ # SKILL.md + scripts/corpus_search.py
    if-actionability/   # SKILL.md
    if-judge/           # SKILL.md + scripts/blind_transform.py
    if-composer/        # SKILL.md
    if-safety/          # SKILL.md

$IF_ROOT/
    graph/
        questions/          # Q-*.yaml (Question Object 1파일 1질문)
        claims/             # C-*.yaml
        edges.jsonl         # 관계 append-only
    corpus/
        question_index/     # 기존 질문 임베딩/키워드 인덱스
    memory/
        decisions.jsonl     # 채택/기각/사유 append-only
        failure_patterns.md
    runs/
        RUN-YYYYMMDD-N/     # 실행 단위 산출물·감사 로그
    dissent/
        dissent_log.jsonl
```

### 2.3 실행 토폴로지

PAO 전제를 그대로 계승한다: **LWAR 세션 기동 주체는 사람**이며, OA는 워커를 띄우지 않는다. OA는 메일박스에 태스크를 발행하고, 사용자가 띄운 이종 LWAR들(구독형 CLI)이 ADP 루프로 수신·실행·제출한다. 기본 운영 방식도 PAO와 동일하게 "동일 작업을 전체 LWAR에 병렬 실행 → 다각 시각 수집"이되, IF에서는 OA가 **배분표(operator/evidence/objective)** 로 의도적 차이를 주입하는 점이 다르다.

---

## 3. Layer 0 — 공용 기반

## 3.1 if-core

모든 스킬이 참조하는 규약의 단일 출처(single source of truth). 이 스킬이 확정되어야 나머지 스킬의 I/O가 고정된다.

```
IfCore // 공통 규약 스킬 (designing) @v:0.1
    QuestionObjectSchema // Question Object YAML 스키마 (designing)
    OperatorRegistry // 질문 연산자 정의 (designing)
    HardGates // 필수 통과 게이트 정의 (designing)
    ValueDimensions // 가치 평가 축 정의 (designing)
    StateMachine // 질문 상태머신 (designing)
    UnknownTaxonomy // Unknown 10분류 (designing)
    DissentSchema // 반론·소수의견 기록 형식 (designing)
```

### 3.1.1 Question Object 스키마 (`schemas/question.yaml`)

```yaml
# Question Object v0.1 — 1파일 1질문, $IF_ROOT/graph/questions/Q-*.yaml
question_id: Q-2026-0001
version: 1                      # 개정 시 증가, 이전 버전은 revisions/에 보존
status: SEED                    # StateMachine 참조
question: ""                    # 질문 본문 (표준화 표현)
question_class: ""              # phenomenon|cause|assumption_inversion|scenario|design|normative|meta
operator: ""                    # OperatorRegistry의 연산자 ID
target_concepts: []             # 대상 개념
unknown_type: ""                # UnknownTaxonomy 분류

why_matters: ""                 # 왜 지금 이 질문인가
assumptions: []                 # 명시된 전제
unknowns: []                    # 미지수
evidence:                       # 근거 (없으면 Hard Gate 탈락)
  - source: ""
    claim: ""
    confidence: 0.0
contradictions: []              # 관련 모순

falsifier: ""                   # 반증 조건 (없으면 Hard Gate 탈락)
minimal_test: ""                # 최소 결정적 테스트
action_plan: ""                 # if-actionability가 생성한 최소 실행계획
estimated_cost: ""              # 시간/비용 개략

scores:                         # if-judge 기록 (블라인드 평가 후)
  novelty: null                 # 외부 그라운딩 기반만 유효
  impact: null
  testability: null
  actionability: null
  grounding: null
  safety: null
  diversity_contribution: null
gate_results: {}                # HardGates 통과 기록

lineage:
  parents: []                   # 파생 원본 질문 ID
  children: []
  derived_from_claims: []
  generated_by: ""              # lwar_id (심사 시 은닉, 저장 시 기록)
  evidence_pack: ""             # 배분받은 증거 팩 ID
  objective: ""                 # 배분받은 목표함수 ID
  run_id: ""

dissent: []                     # 살아남은 반론 (DissentSchema)
human_review:
  status: pending               # pending|adopted|rejected|deferred
  reviewer: ""
  note: ""
created_at: ""
last_verified_at: ""
```

### 3.1.2 Operator Registry (`operators/registry.yaml`)

```yaml
# 질문 공간 변환 연산자 — OA가 LWAR별로 배분하여 발산 다양성 강제
operators:
  - {id: OP-CONTRA,   name: Contradiction,        template: "A와 B가 동시에 사실일 수 없는 이유는?"}
  - {id: OP-INVERT,   name: AssumptionInversion,  template: "A의 핵심 가정이 거짓이라면 무엇이 발생하는가?"}
  - {id: OP-BOUND,    name: Boundary,             template: "A는 어느 조건에서 더 이상 성립하지 않는가?"}
  - {id: OP-SCALE,    name: Scaling,              template: "A가 1000배 커지면 어떤 새 현상이 나타나는가?"}
  - {id: OP-XDOM,     name: CrossDomain,          template: "타 분야 원리 X를 A에 적용하면?"}
  - {id: OP-MISSVAR,  name: MissingVariable,      template: "현재 모델이 빠뜨린 변수는?"}
  - {id: OP-CAUSAL,   name: Causal,               template: "A-B 상관을 만드는 실제 원인은?"}
  - {id: OP-MEASURE,  name: Measurement,          template: "우리가 A를 잘못 측정하고 있지 않은가?"}
  - {id: OP-CF,       name: Counterfactual,       template: "A가 없었다면 B는 발생했을까?"}
  - {id: OP-2ND,      name: SecondOrder,          template: "A 성공 시 2차 효과는?"}
  - {id: OP-ADV,      name: Adversarial,          template: "A를 실패시키는 가장 쉬운 방법은?"}
  - {id: OP-REGIME,   name: RegimeChange,         template: "환경이 변하면 기존 법칙은 언제 역전되는가?"}
meta:
  discovery_allowed: true       # LWAR이 신규 연산자 제안 가능 → OA 승인 후 registry 등록
```

### 3.1.3 Hard Gates (`gates/hard_gates.yaml`)

순서대로 평가하며 하나라도 실패 시 즉시 기각(REJECTED, 사유 기록).

```yaml
gates:
  - {id: G1-GROUND,  rule: "evidence 항목 1개 이상, source 실재 확인"}
  - {id: G2-DUP,     rule: "corpus 대조 중복 아님 (if-novelty-checker 판정)"}
  - {id: G3-CLEAR,   rule: "대상·조건·변수 명확 (모호어 검출 시 탈락)"}
  - {id: G4-UNKNOWN, rule: "실제 미지 존재 (이미 답이 확립된 질문 아님)"}
  - {id: G5-PATH,    rule: "답 획득 경로 존재 (관찰/실험/데이터/시뮬레이션 중 1)"}
  - {id: G6-FALSIFY, rule: "falsifier + minimal_test 기재"}
  - {id: G7-ACTION,  rule: "action_plan 생성 성공 (if-actionability)"}
  - {id: G8-SAFETY,  rule: "if-safety 고위험 플래그 없음 (있으면 격리 버킷)"}
```

### 3.1.4 상태머신

```text
SEED → DEBATED → GATED → SCORED → REVIEWED ─┬→ ADOPTED
  │        │        │                        ├→ REJECTED
  │        │        └→ REJECTED(게이트 탈락)  └→ DEFERRED
  │        └→ MERGED(중복 통합)
  └→ DORMANT(현재 검증 불가) ←→ 재활성화 스캔(if-graph)
```

## 3.2 if-graph

```
IfGraph // Question Graph I/O 스킬 (designing) @dep:IfCore
    WriteQuestion // Q-*.yaml 저장 + edges 기록 (designing)
    QueryDuplicates // 유사/중복 질문 조회 (designing)
    QueryLineage // 계보 추적 (designing)
    ScanDormant // 휴면 질문 재활성화 후보 스캔 (designing)
```

```python
def write_question(q: QuestionObject) -> str:
    """질문 저장. edges.jsonl에 관계 append."""
    # acceptance_criteria:
    #   - 스키마 검증 통과 (필수 필드 전부)
    #   - question_id 유일성
    #   - edges: derived_from/parents/contradicts 전부 기록

def scan_dormant(new_evidence: list[Evidence]) -> list[str]:
    """신규 증거·기술 변화 시 DORMANT 질문 재평가 후보 반환."""
    candidates = [q for q in load_status("DORMANT")]
    return [q.question_id for q in candidates
            if AI_assess_feasibility_change(q, new_evidence) > 0.6]
```

## 3.3 if-memory

```
IfMemory // 탐구 기억 스킬 (designing) @dep:IfCore
    RecordDecision // 채택/기각/사유 기록 (designing)
    QueryFailurePatterns // 반복 실패 패턴 조회 (designing)
    FeedbackIngest // 실험/조사 결과 반영 (designing)
```

```python
# decisions.jsonl 레코드
record = {"question_id": str, "decision": Literal["adopted","rejected","deferred"],
          "reason": str, "reviewer": str, "ts": str}

def query_failure_patterns(domain: str) -> list[str]:
    """생성 전 LWAR에게 주입할 '피해야 할 패턴' 목록."""
    # criteria: 최근 N회 기각 사유를 AI_cluster_reasons로 군집화하여 상위 패턴 반환
```

---

## 4. Layer 1 — 오케스트레이션

## 4.1 if-oa (pao-oa 확장)

pao-oa의 등록 승인·태스크 발행·결과 검증·복구를 계승하고, IF 파이프라인 구동과 **발산/수렴 제어(HELIX explore/exploit)** 를 추가한다.

```
IfOa // IF 오케스트레이션 에이전트 (designing) @v:0.1
    Bootstrap // pao-oa 부트스트랩 + IF_ROOT 초기화 (designing)
    BriefIntake // Inquiry Brief 정규화 (designing)
    AllocationPlan // LWAR별 operator/evidence/objective 배분표 (designing) @dep:BriefIntake
    PhaseController // explore/exploit 단계 전환 제어 (designing)
    TaskPublish // 단계별 태스크 메일박스 발행 (designing) @dep:AllocationPlan
    ResultCollect // 결과 수집·의미 검증 (designing)
    DiversityMonitor // 유사도 감시·강제 발산 주입 (designing) @dep:ResultCollect
    GateRunner // Hard Gates 일괄 판정 위임 (designing)
    RunReport // RUN 단위 감사 보고 (designing)
```

### 4.1.1 Inquiry Brief

```yaml
# 실행 입력 — 사용자가 작성, OA가 정규화
brief_id: RUN-20260813-1
domain: ""                # 탐구 대상
goal: ""                  # discovery|validation|strategy|risk|invention
constraints: []           # 예산/데이터/윤리/보안
forbidden_premises: []    # 금지된 전제
must_consider: []         # 반드시 고려할 관점
success_criteria: ""      # 예: "전문가 채택 질문 N개"
budget:
  max_rounds: 3
  max_questions_per_lwar: 10
```

### 4.1.2 배분표 (AllocationPlan) — 4차원 이종성의 구현체

```python
def build_allocation(brief: Brief, lwars: list[LwarProfile]) -> AllocationTable:
    """LWAR 프로파일(모델·강점) 기반으로 operator/evidence/objective를 서로 다르게 배분."""
    # acceptance_criteria:
    #   - Model Diversity: 동일 모델 계열에 동일 (operator, evidence) 조합 배분 금지
    #   - Evidence Diversity: papers|patents|code|news|failures|regulation|history 분산
    #   - Objective Diversity: importance_max|consensus_falsify|info_per_cost 중 배분
    #   - Epistemic Diversity: operator를 LWAR당 2~3개로 제한 (전 연산자 배분 금지)
    table = {}
    for lwar in lwars:
        table[lwar.id] = {
            "operators": AI_select_operators(lwar, brief, k=3),
            "evidence_pack": AI_assign_evidence_pack(lwar, brief),
            "objective": AI_assign_objective(lwar, brief),
            "avoid_patterns": query_failure_patterns(brief.domain),
        }
    return table
```

### 4.1.3 PhaseController — 발산/수렴 제어

```python
def phase_controller(run: Run) -> None:
    """HELIX explore/exploit 이중나선의 IF 적용."""
    phase = "EXPLORE"  # 합의 금지, 컨텍스트 격리, 독립 생성
    while True:
        results = collect_round(run, phase)
        sim = compute_pairwise_similarity(results)      # 임베딩 코사인 — 실제 코드
        if phase == "EXPLORE":
            if sim.mean > 0.80:                          # 조기 동조화 감지
                inject_divergence(run)                   # 미사용 operator 강제 배분·evidence 재섞기
                continue
            if run.round >= run.brief.budget.max_rounds or AI_assess_coverage(results) >= 0.8:
                phase = "EXPLOIT"                        # 수렴 단계 진입: 교차검토·정제 허용
        else:
            if AI_assess_refinement_saturation(results):
                break
        run.round += 1
```

### 4.1.4 태스크 발행 규칙

- 태스크 페이로드에 **다른 LWAR 산출물 절대 미포함** (EXPLORE 단계).
- EXPLOIT 단계의 반론 태스크에는 대상 질문만 포함하되 `generated_by` 필드 제거(블라인드).
- 심사 태스크는 생성 참여 LWAR 제외 목록을 명시(`exclude_lwars`).

## 4.2 if-lwar (pao-lwar 확장)

```
IfLwar // IF 워커 에이전트 (designing) @v:0.1
    Bootstrap // pao-lwar 부트스트랩 (designing)
    ProfileDeclare // 런타임 프로파일 신고 (designing)
    SkillDispatch // 태스크 role 필드 → 역할 스킬 로드·실행 (designing)
    ResultSubmit // 산출물 스키마 검증 후 제출 (designing)
```

```yaml
# ProfileDeclare — 등록 시 1회 신고, OA 배분 근거
lwar_profile:
  lwar_id: ""
  model_family: ""        # claude|gpt|gemini|grok|deepseek|local...
  strengths: []           # search|code|math|longctx...
  tools: []               # web_search|code_exec...
  cost_class: subscription
```

```python
def skill_dispatch(task: Task) -> Result:
    """태스크의 role에 해당하는 IF 역할 스킬을 로드하여 실행."""
    ROLE_SKILLS = {"unknown_mine": "if-unknown-miner", "generate": "if-question-gen",
                   "contrarian": "if-contrarian", "novelty": "if-novelty-checker",
                   "actionability": "if-actionability", "judge": "if-judge",
                   "compose": "if-composer", "safety": "if-safety"}
    skill = load_skill(ROLE_SKILLS[task.role])
    return skill.run(task.payload)   # 산출물은 if-core 스키마 준수 필수
```

---

## 5. Layer 2 — 역할 스킬

각 스킬의 SKILL.md는 (a) 입출력 스키마, (b) 실행 PPR, (c) acceptance_criteria 3요소로 구성한다. 아래는 각 스킬의 핵심 명세.

## 5.1 if-unknown-miner

```python
def mine_unknowns(evidence_pack: EvidencePack, domain: str) -> list[Unknown]:
    """질문 생성 전, '무엇을 모르는가'부터 탐지."""
    claims = AI_extract_claims(evidence_pack)            # 주장-근거-가정 추출
    unknowns = []
    unknowns += AI_detect_contradictions(claims)          # Contradictory Unknown
    unknowns += AI_detect_hidden_assumptions(claims)      # Hidden Assumption
    unknowns += AI_detect_causal_gaps(claims)             # Causal Unknown
    unknowns += AI_detect_boundary_gaps(claims)           # Boundary Unknown
    unknowns += AI_detect_structural_holes(claims)        # Unknown Unknown Candidate (그래프 단절)
    return [tag_taxonomy(u) for u in unknowns]
    # acceptance_criteria:
    #   - 각 Unknown에 UnknownTaxonomy 분류 태그
    #   - 각 Unknown에 근거 claim ID 연결 (근거 없는 Unknown 금지)
```

## 5.2 if-question-gen

```python
def generate_questions(unknowns: list[Unknown], alloc: Allocation) -> list[QuestionSeed]:
    """배분받은 operator만 사용하여 독립 생성. 타 LWAR 산출물 참조 금지."""
    seeds = []
    for u in unknowns:
        for op in alloc.operators:                        # 배분된 2~3개만
            q = AI_apply_operator(u, op, objective=alloc.objective)
            if q and q not in seeds:
                seeds.append(QuestionSeed(question=q, operator=op.id,
                                          unknown_ref=u.id, evidence_refs=u.claim_ids))
    seeds = [s for s in seeds if not AI_match_pattern(s, alloc.avoid_patterns)]
    return seeds[: alloc.max_questions]
    # acceptance_criteria:
    #   - 모든 seed에 operator + unknown_ref + evidence_refs 존재
    #   - avoid_patterns 매칭 seed 0건
    #   - 신규 operator 발견 시 별도 proposal로 제출 (registry 직접 수정 금지)
```

## 5.3 if-contrarian

```python
DISSENT_TYPES = ["evidence", "logic", "premise", "alternative", "stakeholder", "execution"]

def cross_examine(question: QuestionSeed) -> DissentReport:
    """구조화 반론 6유형 전부 시도. '무난한 비판' 금지 — 기각 사유를 입증하려는 공격."""
    report = DissentReport(question_id=question.id)
    for dtype in DISSENT_TYPES:
        attack = AI_generate_attack(question, dissent_type=dtype)
        survived = AI_assess_survival(question, attack)
        report.add(dtype, attack, survived)
    report.verdict = "SURVIVED" if report.survival_rate >= 0.5 else "KILLED"
    return report
    # acceptance_criteria:
    #   - 6유형 전부 기록 (생략 금지)
    #   - KILLED여도 report는 dissent_log에 보존 (Dissent Preservation)
    #   - 살아남은 반론은 Question Object의 dissent 필드로 이관
```

## 5.4 if-novelty-checker

```python
def check_novelty(question: QuestionSeed) -> NoveltyReport:
    """외부 그라운딩만 유효. LLM 자체 판단은 참고 불가."""
    # 1. 내부 코퍼스 대조 (결정론적)
    internal = corpus_search(question.text, index="$IF_ROOT/corpus/question_index")
    # 2. 외부 검색 (web/논문/특허)
    external = web_search_prior_art(question.text)
    # 3. 판정
    duplicates = [h for h in internal + external if h.similarity > 0.85]
    verdict = "DUPLICATE" if duplicates else \
              "VARIANT" if any(h.similarity > 0.70 for h in internal + external) else "NOVEL"
    return NoveltyReport(verdict=verdict, closest=top3(internal + external),
                         evidence_urls=[h.url for h in external[:5]])
    # acceptance_criteria:
    #   - closest 3건 반드시 첨부 (판정 근거 추적성)
    #   - 검색 0건이어도 "NOVEL" 자동 부여 금지 → AI_reformulate_query 후 재검색 1회
```

## 5.5 if-actionability

```python
def actionability_gate(question: QuestionSeed) -> ActionReport:
    """최소 실행계획 생성 실패 = 기각. 철학 질문과 연구 질문을 가르는 실용 기준."""
    plan = AI_design_minimal_test(question)   # 실험/조사/시뮬레이션/데이터분석 중 1
    if plan is None:
        return ActionReport(verdict="FAIL", reason="minimal test 설계 불가")
    falsifier = AI_derive_falsifier(question, plan)
    cost = AI_estimate_cost(plan)
    return ActionReport(verdict="PASS", action_plan=plan,
                        falsifier=falsifier, estimated_cost=cost)
    # acceptance_criteria:
    #   - PASS 시 plan에 {방법, 필요 데이터, 측정 지표, 판정 기준} 4요소 필수
    #   - falsifier는 "어떤 결과가 나오면 질문 전제가 기각되는가" 형식
```

## 5.6 if-judge

```python
def judge(batch: list[QuestionObject], exclude_lwars: list[str]) -> list[ScoreCard]:
    """블라인드 평가. 생성 참여자 제외는 OA가 보장, 스킬은 검증만."""
    assert current_lwar_id() not in [q.lineage.generated_by for q in batch]
    scored = []
    for q in batch:
        blind = blind_transform(q)            # 모델명·문체 제거, 표준화 표현으로 변환 (스크립트)
        if not run_hard_gates(blind):         # G1~G8 — 결정론 우선, AI 판단은 G3/G4만
            scored.append(ScoreCard(q.id, verdict="GATE_FAIL", gate=failed_gate))
            continue
        card = ScoreCard(q.id,
            impact=AI_assess_impact(blind),
            testability=AI_assess_testability(blind),
            grounding=score_grounding(blind),              # evidence 링크 수·신뢰도 — 결정론
            novelty=blind.novelty_report.verdict_score,    # if-novelty-checker 결과만 사용
            actionability=blind.action_report.verdict_score,
            diversity_contribution=AI_assess_portfolio_gap(blind, current_portfolio()))
        scored.append(card)
    return scored
    # acceptance_criteria:
    #   - novelty 점수를 AI_가 직접 산출한 경우 무효 (novelty mirage 방지)
    #   - 단일 scalar 종합점수 금지 — 축별 점수 유지 (Pareto 선별은 OA/Composer 몫)
```

## 5.7 if-composer

```python
def compose(seed: QuestionSeed, dissent: DissentReport, novelty: NoveltyReport,
            action: ActionReport, scores: ScoreCard) -> QuestionObject:
    """생존 질문을 Question Object 완성형으로 조립 후 그래프 등록."""
    q = QuestionObject.from_seed(seed)
    q.dissent = dissent.survived_items
    q.scores = scores.as_dict()
    q.falsifier, q.minimal_test = action.falsifier, action.plan
    q.action_plan = action.plan.summary
    q.status = "SCORED"
    normalize_language(q)                     # 표준화 표현 — 스크립트
    write_question(q)                         # if-graph 위임
    return q
    # acceptance_criteria:
    #   - 스키마 필수 필드 100% 충족
    #   - MERGED 처리: novelty VARIANT 판정 시 closest와 병합 제안 첨부
```

## 5.8 if-safety

```python
def safety_review(q: QuestionObject) -> SafetyReport:
    checks = {"dual_use": AI_assess_dual_use(q), "privacy": AI_assess_privacy_risk(q),
              "bias": AI_assess_bias_amplification(q), "regulation": AI_assess_regulatory_risk(q)}
    if any(v.level == "HIGH" for v in checks.values()):
        quarantine(q)                         # 고위험 격리 버킷 — 삭제 아님, 인간만 열람
        return SafetyReport(verdict="QUARANTINE", checks=checks)
    return SafetyReport(verdict="PASS", checks=checks)
```

---

## 6. Layer 3 — 파이프라인

### 6.1 InquiryRun — 1회 탐구 사이클

```
InquiryRun // 1회 실행 정의 (designing) @v:0.1
    S1_BriefIntake // Brief 정규화 (designing)
    S2_Allocation // 배분표 생성 (designing) @dep:S1_BriefIntake
    S3_UnknownMining // 전 LWAR 병렬, 각자 evidence pack (designing) @dep:S2_Allocation
    S4_IndependentGen // 독립 발산 생성 — EXPLORE (designing) @dep:S3_UnknownMining
    S5_DiversityCheck // 유사도 감시, 필요 시 S4 재시행 (designing) @dep:S4_IndependentGen
    S6_CrossExam // 교차 반론 — EXPLOIT 진입, 블라인드 (designing) @dep:S5_DiversityCheck
    S7_NoveltyAction // [parallel] 신규성 검증 + 실행 게이트 (designing) @dep:S6_CrossExam
    S8_Judge // 블라인드 평가, 생성자 제외 (designing) @dep:S7_NoveltyAction
    S9_Compose // Question Object 조립·그래프 등록 (designing) @dep:S8_Judge
    S10_SafetyGate // 안전 점검·격리 (designing) @dep:S9_Compose
    S11_HumanReview // 인간 승인 관문 (designing) @dep:S10_SafetyGate
    S12_Feedback // 결정·사유 memory 기록 (designing) @dep:S11_HumanReview
```

```python
def inquiry_run(brief: Brief) -> RunReport:
    alloc = build_allocation(brief, registered_lwars())
    unknowns = publish_and_collect("unknown_mine", alloc)          # S3: 전 LWAR 병렬
    while True:                                                     # S4-S5: EXPLORE 루프
        seeds = publish_and_collect("generate", alloc)
        if diversity_ok(seeds) or alloc.rounds_exhausted():
            break
        alloc = inject_divergence(alloc)
    dissents = publish_and_collect("contrarian", cross_assign(seeds))   # S6: 자기 질문 반론 금지
    survivors = [s for s in seeds if dissents[s.id].verdict == "SURVIVED"]
    [parallel]
    novelty = publish_and_collect("novelty", survivors)
    action  = publish_and_collect("actionability", survivors)
    [/parallel]
    scores = publish_and_collect("judge", survivors, exclude=generators_of(survivors))
    objects = [compose(s, dissents[s.id], novelty[s.id], action[s.id], scores[s.id])
               for s in survivors if scores[s.id].verdict != "GATE_FAIL"]
    objects = [q for q in objects if safety_review(q).verdict == "PASS"]
    portfolio = select_pareto(objects, axes=["novelty", "impact", "actionability"])
    return RunReport(portfolio=portfolio, awaiting_human_review=True)
    # acceptance_criteria:
    #   - Phase1 성공 기준: portfolio ≥ 10, 인간 채택 ≥ 1
    #   - 전 질문 provenance 완결 (lineage 필드 공란 0건)
    #   - dissent_log에 KILLED 질문 반론 전량 보존
```

### 6.2 HumanReview / FeedbackLoop

- 인간은 `$IF_ROOT/runs/RUN-*/review.md`에서 질문 카드를 검토, `adopt|reject|defer` + 사유 기입.
- `if-memory.record_decision`이 결정을 축적 → 다음 RUN의 `avoid_patterns`와 (장기적으로) 평가 가중치 학습 데이터가 된다.
- 실험/조사 결과가 생기면 `feedback_ingest` → `scan_dormant` 트리거 → 휴면 질문 재활성화.

---

## 7. Claude Code 구현 계획

### 7.1 구현 Gantree (착수 순서)

```
IfImplementation // Claude Code 구현 (designing) @v:0.1
    M1_IfCore // 스키마·registry·gates YAML + 검증 스크립트 (designing)
        SchemaFiles // question.yaml, brief.yaml, dissent.yaml (designing)
        ValidatorScript // scripts/validate.py — 스키마 검증 CLI (designing)
        # criteria: 샘플 Question Object 3건이 검증 통과/실패를 정확히 판별
    M2_GraphMemory // if-graph, if-memory 스크립트 (designing) @dep:M1_IfCore
        GraphIo // graph_io.py — write/query/lineage/dormant-scan (designing)
        MemoryIo // memory_io.py — decisions.jsonl append/query (designing)
    M3_Orchestration // if-oa, if-lwar 스킬 (designing) @dep:M2_GraphMemory
        OaSkill // pao-oa 복제 + Brief/Allocation/Phase/Publish 확장 (designing)
        LwarSkill // pao-lwar 복제 + Profile/SkillDispatch 확장 (designing)
        # criteria: OA 발행 태스크를 LWAR 1대가 수신→역할스킬 실행→제출 완주
    M4_MvpRoles // MVP 역할 스킬 4종 (designing) @dep:M3_Orchestration
        [parallel]
        GenSkill // if-question-gen (designing)
        ContrarianSkill // if-contrarian (designing)
        JudgeSkill // if-judge + blind_transform.py (designing)
        ComposerSkill // if-composer (designing)
        [/parallel]
    M5_MvpRun // 단일 도메인 E2E 실행 (needs-verify) @dep:M4_MvpRoles
        # criteria: LWAR 3대(이종 모델) × 1 Brief → portfolio ≥ 10 → 인간 리뷰 완료
    M6_Phase2Roles // 검증 강화 스킬 4종 (blocked) @dep:M5_MvpRun
        UnknownMinerSkill // if-unknown-miner (blocked)
        NoveltySkill // if-novelty-checker + corpus_search.py (blocked)
        ActionSkill // if-actionability (blocked)
        SafetySkill // if-safety (blocked)
```

MVP(M1~M5)에서는 S3(Unknown Mining)·S7(Novelty/Action)·S10(Safety)을 생략하고, 게이트 중 G2/G7/G8을 인간 리뷰로 대체한다. 이종성·반론·블라인드 심사·Question Object라는 핵심 가설을 최소 구성으로 먼저 검증한다.

### 7.2 결정론/AI 경계 (구현 시 준수)

| 결정론 코드 (Python 스크립트) | AI 인지 (`AI_` — 스킬 본문) |
|---|---|
| 스키마 검증, edges 기록, 유사도 계산(임베딩 코사인), 코퍼스 검색, 블라인드 변환, jsonl I/O, Pareto 선별 | claim 추출, unknown 탐지, operator 적용, 반론 생성·생존 판정, impact/testability 평가, 병합 제안 |

### 7.3 미확정 사항 (구현 전 결정 필요)

1. `IF_ROOT` 버스를 PAO 버스와 물리적으로 공유할지(태스크는 PAO 메일박스, 데이터만 IF_ROOT) — **권장: 공유** (기존 pao_runtime 무수정 재사용).
2. 임베딩 백엔드(코퍼스 인덱스·유사도 계산) — 로컬 모델 vs API. MVP는 로컬 권장.
3. review.md 인터페이스 vs 간이 웹 대시보드 — MVP는 파일 기반 권장.

---

## 부록 A. 태스크 페이로드 형식 (버스 계약)

```yaml
# OA → LWAR 메일박스 태스크 (pao 태스크 봉투에 payload로 탑재)
task:
  run_id: RUN-20260813-1
  role: generate            # unknown_mine|generate|contrarian|novelty|actionability|judge|compose|safety
  phase: EXPLORE            # EXPLORE|EXPLOIT
  payload:
    allocation: {...}       # role=generate: 배분표 해당 LWAR 항목
    questions: [...]        # role=contrarian/judge 등: 대상 질문 (블라인드 처리됨)
    exclude_lwars: [...]    # role=judge
  output_schema: question_seed | dissent_report | novelty_report | action_report | score_card
```

## 부록 B. 용어

| 용어 | 정의 |
|---|---|
| Question Object | 질문을 추적·검증·진화 가능한 구조화 객체로 표현한 YAML 단위 |
| Operator | Unknown을 질문으로 변환하는 명명된 연산자 (질문 문법의 단위) |
| Allocation | OA가 LWAR별로 operator/evidence/objective를 다르게 배분한 표 — 이종성 구현체 |
| EXPLORE/EXPLOIT | 발산(합의 금지)/수렴(정제 허용) 단계 — HELIX 이중나선의 IF 적용 |
| Dissent Preservation | 기각된 질문의 반론까지 전량 보존하는 원칙 |
| DORMANT | 현재 검증 불가하나 환경 변화 시 재활성화 대상인 질문 상태 |
