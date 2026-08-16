# REVIEW-InquiryFoundry-Workplan

## Scope
- Target: `.pgf/WORKPLAN-InquiryFoundry.md`
- Source DESIGN: `.pgf/DESIGN-InquiryFoundry.md` @v:0.2.3
- Date: 2026-08-14
- Mode: PGF plan-review (convert 규칙 + P5/P7/P8)
- Iterations: 1 (조상 게이트·IfOa/IfLwar parallel 반영)

## Summary

DESIGN Gantree 22노드를 실행 트리로 옮겼다. PPR은 복제하지 않았다. `IfPhase2Roles (blocked)`를 유지했다. 무의존 리프 4종(SchemaPack/OperatorPack/GatePack/StatePack)을 `in-progress`로 열었다. 역할 노드에 DESIGN에 없던 `@dep:SchemaPack`을 넣어 조기 착수를 막았다.

## Verdict

| Perspective | 판정 |
|---|---|
| Feasibility (P5) | PASS |
| Risk (P7) | PASS + notes |
| Architecture (P8) | PASS (dep 정합 1회 개정) |
| **Aggregate** | **APPROVED** — Critical=0, High=0 |

## Convert-rule check

| 규칙 | 결과 |
|---|---|
| POLICY 존재 | PASS — halt, all_done_or_blocked, V1–V18 |
| DESIGN 노드 1:1 (22) | PASS |
| PPR 미복제 | PASS |
| DESIGN `(blocked)` 유지 | PASS — IfPhase2Roles |
| 무의존 선두 `in-progress` | PASS — IfCore 리프 4 + 그룹 |
| status JSON 동기 | PASS — in-progress 6, designing 15, blocked 1 |
| `@dep` 비순환 | PASS |
| 빌드 게이트 ≠ SLO | PASS |

## Findings

### [medium][plan] 실행 `@dep`가 DESIGN보다 타이트하다
- Evidence: WORKPLAN `IfGenerate/IfContrarian/IfJudge @dep:SchemaPack`, `Allocate @dep:IfRuntime`. DESIGN Gantree에는 없음.
- Impact: 구현 순서는 안전해지고, DESIGN 트리만 보면 역할 스킬이 스키마 없이 시작 가능해 보인다.
- Resolution: **accepted** — 실행 의존. DESIGN 구조 트리를 바꾸지 않는다. 본 리뷰에 기록.

### [medium][feasibility] SchemaPack이 15분 원자 규칙을 넘길 수 있다
- Evidence: schemas 10종 + validate.py + V4/V10/V16.
- Impact: execute 시 한 노드가 길면 재개 단위가 커진다.
- Recommendation: execute가 쪼개되 WORKPLAN 노드 이름은 유지. 산출물 단위로 commit.

### [low][risk] `on_blocked: halt`가 라이브 M5를 통째로 멈출 수 있다
- Evidence: M5 라이브 LWAR≥3은 사람 기동. 한 LWAR 부재 = Blocked.
- Resolution: POLICY 유지. 라이브는 CI가 아니다. fixture M5와 라이브 M5를 수락 조건에서 이미 분리함.

## Residual (설계에서 이관)

- jail = PAO permissions 근사. v0.3 TaskJail.

## Next

`/PGF execute InquiryFoundry` — W0 `SchemaPack`부터. 그룹 `IfCore`를 done으로 올리지 말 것(StoreIo/BusContract 남음).
