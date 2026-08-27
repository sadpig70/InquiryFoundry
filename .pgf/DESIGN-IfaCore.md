# IfaCore Design @v:0.1.0

**Status** done (v0.1.0 구현·파일럿 검증 2026-08-27) · **Notation** PG v1.3 + PGF v2.5 · **Scale** Level 3 (15 nodes)
**이름** `ifa` — 운영자 지정. 산출물이 대답이 아니라 **예측**이라는 구분은 이름이 아니라
**스키마가 강제한다**(A3). **권위**: 이 문서. 기존 IF 권위 설계는 무변경.

## Purpose

IF 가 채택한 질문(현재 113건)에 대해, 같은 방법론(가시성 감옥 · 이종 벤더 · 교차 반박 ·
블라인드 채점 · 출처 가린 리뷰 · 기계 종결 불가)으로 **사전 등록 예측 포트폴리오**를
생산한다. 산출물은 (1) 질문별 3벤더 독립 예측 + kill_condition, (2) 벤더 간 불일치
점수 — **실제 실험의 정보 이득 순위**. §7.22(채택물의 소비자 부재)의 첫 소비자다.

## Closed Decisions

| ID | Decision |
|---|---|
| A1 | **완전 독립.** 스킬 `.agents/skills/ifa-core/`, 저장소 `.ifa/`. `.if` 에는 **쓰기 0바이트** — ADOPTED 질문 읽기만. `.ifa` 는 `.if` 와 같은 git 제외 |
| A2 | `if_core` 는 **역할 무관 유틸만 import** (`ensure_jail`, `load_yaml`/`atomic_write_yaml`, `mint_anon`, `load_role_outbox`). 원본 파일 무수정 |
| A3 | AnswerObject 의 `kind` enum 은 **`["predicted"]` 단일값**. `answered` 는 스키마에 존재하지 않는다 — 실제 실험이 수행되는 날 그 값의 추가가 명시적 스키마 변경이 되도록 |
| A4 | **단방향 참조** — AnswerObject 가 `question_id` 를 든다. QO 는 필드 하나 안 붙는다 |
| A5 | 파이프라인 `predict → rebut → adjudicate → review`. 자기 예측을 자기가 반박·채점하지 않는다(회전 배정). 예측은 벤더 간 **상호 불가시**(감옥) |
| A6 | **IF 런과 IFA 런 동시 실행 금지** (버스 다중 세입자 미검증 — 검증 전 운영 규칙) |
| A7 | task_id 네임스페이스 `task-ifa-…`, workflow `workflow-ifa-…` |
| A8 | 예측 필수 필드: `question_id`, `prediction`(질문의 reject_if 좌표로 방향·크기), `rationale`, `confidence`(low/medium/high), `kill_condition`(무엇이 관측되면 이 예측이 죽는가), `evidence`(코퍼스 인용 ≥1) |
| A9 | 상태 `DRAFT → SCORED → REGISTERED | DISCARDED`. **REGISTERED 는 리뷰어 비공란 + 비준에서만** — `preflight_close` 가 거절(IF Invariant 10 상속). "채택"이라는 낱말을 쓰지 않는다 — 질문 채택과 혼동 방지 |
| A10 | 마감 산출물에 **질문별 불일치 점수**: 3벤더 예측 방향의 일치도(agree/split/diverge). diverge = 실험 정보 이득 최상위 |
| A11 | **워커 측 디스패처 없음.** 역할 계약 전문을 inbox YAML 에 싣고, 검증은 OA 측 collect 후 수행. 무효 outbox 는 drop 으로 기록(fail-safe). ifa-lwar 스킬을 만들지 않는다 |
| A12 | `ifa_core/bus.py` 는 `if_core.bus` 의 **적응 복사**다 — `make_pao_task` 가 IF 역할·디스패처에 결합돼 import 불가. 두 번째 진실 원천의 비용을 명시적으로 지불하며, 계약 변경 시 양쪽을 함께 본다는 주석을 남긴다 |
| A13 | 되먹임 루프(회피·장부·복원) **없음** — 파일럿 범위 밖. 필요가 실측되면 그때 |

## Layout

```text
.agents/skills/ifa-core/
    ifa_core/
        __init__.py
        store.py       # .ifa 경로, 질문 읽기(.if 읽기 전용), AnswerObject 저장, 상태
        schema.py      # 수제 검증: predict/rebut/adjudicate outbox, answer object
        bus.py         # 적응 복사 (A12): make_task + publish_collect
        cycle.py       # select → predict → rebut → adjudicate → compose → review → close
        roles.py       # 역할 계약 전문 (inbox 에 실림, A11)
    scripts/ifa.py     # CLI: select | run | review-run | ratify | close | report
.ifa/
    runs/RUN-.../      # jail/, allocation, batch
    graph/answers/     # ANS-... yaml (kind: predicted)
    reports/           # priorities.md (A10)
```

## Gantree

```
IfaCore // 예측 포트폴리오 파이프라인 (done) @v:0.1.0
    Store // .ifa 저장소 + .if 읽기 전용 접근 (done)
        # criteria: .if 아래 어떤 파일도 열기-쓰기 모드로 열지 않는다
    Schema // 수제 검증기 (done)
        # criteria: kind 는 predicted 만, evidence>=1, kill_condition 비공란
    Roles // 역할 계약 3종 전문 (done)
    Bus // 적응 복사 publish_collect (done) @dep:Store
    Select // ADOPTED 에서 배치 선별 (done) @dep:Store
        # process: 정량 reject_if 를 가진 질문 우선, 도메인 혼합
    Predict // 3벤더 독립 예측 (done) @dep:Bus,Roles,Select
    Rebut // 회전 배정 교차 반박 (done) @dep:Predict
        # criteria: 자기 예측 반박 0 (배정표로 강제)
    Adjudicate // 블라인드 채점 (done) @dep:Rebut
        # criteria: anon_id 만, 벤더·자기 예측 채점 불가
    Compose // AnswerObject 조립 DRAFT->SCORED (done) @dep:Adjudicate
    Review // 출처 가린 리뷰 + 비준 + preflight (done) @dep:Compose
    Report // 불일치 점수 + 우선순위 (done) @dep:Review
    UnitTests // pytest tests/ifa (done) @dep:Report
    Pilot // 실 LWAR 파일럿 1런 (done) @dep:UnitTests
    Verify // 3관점 교차 검증 (done) @dep:Pilot
    Docs // README + HANDOFF + gitignore (done) @dep:Verify
```

## PPR

### Select

```python
def select_batch(n: int = 6) -> list[QO]:
    """정량 판정이 명확한 채택 질문을 도메인 섞어 고른다."""
    adopted = read_if_adopted()                      # .if 읽기 전용
    scored = [q for q in adopted if has_quant_reject_if(q)]
    return mix_domains(scored)[:n]
    # criteria: 선별 근거가 batch.yaml 에 남는다. .if 무변경
```

### Predict inbox 계약 (roles.py 전문 요약)

```python
# 각 질문에 대해:
#   prediction: reject_if 의 좌표로 — "기각된다/기각되지 않는다 + 예상 방향·크기"
#   rationale: 코퍼스 근거로 3문장 이상
#   confidence: low|medium|high
#   kill_condition: 이 예측을 죽이는 관측 1개 (질문의 falsifier 와 달라야 함)
#   evidence: papers/... >=1
# 금지: 다른 벤더 예측 참조(볼 수 없음), 새 실험 설계 제안, 질문 수정
```

### Compose + 불일치

```python
def disagreement(preds: list) -> str:
    dirs = [p.direction for p in preds]              # reject | no-reject
    return "agree" if len(set(dirs)) == 1 else (
        "diverge" if len(set(dirs)) == len(dirs) else "split")
    # criteria: diverge > split > agree 순으로 priorities.md 정렬
```

## Invariants (IF 에서 상속, ifa 에 재강제)

1. `.if` 쓰기 0바이트 (Store 가 경로를 열 때 검사)
2. 예측 상호 불가시 · 자기 반박/채점 금지 (배정표)
3. `REGISTERED` 는 리뷰어 비공란 + 비준에서만
4. AnswerObject `kind` == `predicted` 불변
5. 리뷰 패킷에 벤더·기계 점수 비노출
