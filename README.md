# InquiryFoundry

다종 AI 런타임이 서로 다른 지식·관점·반론을 교차시켜, **검증 가능하고 행동 가능한 질문(Question Object)** 포트폴리오를 만드는 Inquiry Intelligence System.

최적화 대상은 답이 아니라 질문이다. 문장 novelty가 아니라 다음에 가깝다.

```text
value ≈ expected_knowledge_change × importance × answerability
output = Pareto portfolio of Question Objects
```

현재 상태: **v0.2.3 execute**. `if-core` + 역할 스킬 + 로컬 pytest. 라이브 인지 런 `RUN-20260815-live2`는 compose까지 수행, human adopt 대기. Phase2 (`IfPhase2Roles`) blocked.

---

## 권위 문서

| 문서 | 역할 |
|---|---|
| [`.pgf/DESIGN-InquiryFoundry.md`](.pgf/DESIGN-InquiryFoundry.md) | **권위 설계** v0.2.3 (PG + PGF) |
| [`.pgf/REVIEW-InquiryFoundry.md`](.pgf/REVIEW-InquiryFoundry.md) | 3시각 design-review, 개정 기록 |
| [`.pgf/WORKPLAN-InquiryFoundry.md`](.pgf/WORKPLAN-InquiryFoundry.md) | 실행 계획 @v:0.2.3 |
| [`.pgf/status-InquiryFoundry.json`](.pgf/status-InquiryFoundry.json) | 노드 상태 (22 nodes) |
| [`_legacy/`](_legacy/) | 탐구 원본. 참고만 |
| [`docs/PAO_TechSpec.md`](docs/PAO_TechSpec.md) | 의존 런타임 PAO 기술 개요 |

초안과 설계가 다르면 **`.pgf/DESIGN-InquiryFoundry.md`를 따른다.**

---

## 한 줄 구조

```text
Brief → 이종 배분(Allocate)
  → EXPLORE: 가시성 감옥 안에서 미지 탐지 → 질문 생성
  → 다양성 실패 시 런 중지 (강제 수용 없음)
  → EXPLOIT: 반론 → 블라인드 심사
  → Compose(결정론) → 인간 review.yaml → 채택
```

정상 런은 **LWAR ≥ 3** (생성자 ≠ 반론자 ≠ 심사자). 2대는 ablation이며 `ADOPTED`가 금지된다. `ADOPTED`는 인간만 부여한다.

스킬은 역할이고, 이종성은 스킬이 아니라 **배분표**(operator / evidence / objective / vendor family)에서 나온다.

---

## 저장소 배치

```text
.pgf/                 # 권위 설계·검토·상태
.agents/skills/       # 로컬 스킬 (pg, pgf, pao-oa, pao-lwar, …)
docs/                 # 초안·PAO 스펙
_legacy/              # 탐구 원본
_workspace/           # 작업 스크래치
tools/                # PAO 검증·도그푸드 스크립트
AGENTS.md             # 에이전트 운영 계약
```

구현이 시작되면 스킬은 `.agents/skills/if-*`, 데이터는 `IF_ROOT`(기본 `<cwd>/.if`)에 둔다. 태스크 버스는 기존 PAO(`.pao` / `PAO_ROOT`)를 포크하지 않고 호출만 한다.

---

## 에이전트

기본 역할은 OA다. 자세한 계약은 [`AGENTS.md`](AGENTS.md), [`CLAUDE.md`](CLAUDE.md).

- 한국어로 답하고, 코드·명령·식별자는 English.
- 전역 스킬 대신 **로컬** `.agents/skills`만 사용.
- OA는 vendor LWAR을 직접 띄우지 않는다. PAO 파일 버스로만 말한다.
- Python은 PATH의 `python`. 인터프리터 절대 경로 호출 금지.
- Shell: Git Bash 또는 PowerShell 7. PowerShell 5.1 금지.

설계·계획·실행은 PG / PGF 표기를 따른다.

---

## 구현 순서 (설계서)

1. `if-core` — 스키마, 게이트, 상태머신, `validate.py`
2. StoreIo — Question Object / edges / memory
3. PAO 오버레이 — `if-oa`, `if-lwar` (런타임 복사 금지)
4. 역할 스킬 — generate, contrarian, judge
5. InquiryCycle E2E (fixture, 이후 이종 3 LWAR)
6. Phase 2 — unknown-miner, novelty, action, safety (`blocked`)

빌드 게이트는 `qo_count == seed_count && seed_count > 0`이다. `scored ≥ 8`은 SLO이지 CI가 아니다.

---

## 환경

- Python 3 (PATH의 `python`)
- [PAO](.agents/skills/pao-oa) 로컬 스킬 (이미 이 저장소에 포함)
- 이종 CLI 에이전트 세션은 사람이 기동

---

## License

[MIT](LICENSE) · Copyright (c) 2025-2026 sadpig70
