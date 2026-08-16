# InquiryFoundry 핵심 요소 — 8개 AI 에이전트 보고 종합 분석

**입력**: `IF중요요소보고.md` (AI Agent 1~8 독립 보고) · **작성일**: 2026-08-13
**목적**: 다종 멀티에이전트 기반 질문 생산(Inquiry Intelligence) 시스템의 성패를 좌우하는 요소를 교차 검증 기반으로 통합

## 요약

8개 보고를 교차하면 합의는 명확하다. InquiryFoundry의 성패는 질문 **생성**이 아니라 (1) 진짜 이종성 유지, (2) 구조화된 질문 객체(스키마), (3) 외부 그라운딩 기반 평가, (4) 행동 전환 폐루프의 4가지에 달려 있다. "novel하게 질문하라"는 프롬프트는 작동하지 않으며(다양성 붕괴 실측), LLM 자체 novelty 판단은 신뢰 불가(novelty mirage 실측)라는 두 반증 데이터가 전체 설계를 규정한다.

---

## 1. 최적화 목표의 재정의 (전원 합의)

기존 시스템: `Prompt → Candidate → Evaluate → Best Answer`
InquiryFoundry: `Knowledge → Unknown Detection → Question Space Exploration → Question Validation → Inquiry Portfolio`

목적함수는 "참신한 문장"이 아니라 **답했을 때 세계모델이 얼마나 바뀌는가**(Expected Knowledge Change × Importance × Answerability). AutoDiscovery의 Bayesian Surprise 기준(고정 탐색 비용 대비 5~29% 더 많은 surprising discoveries)이 실증 근거.

핵심 전환: 최종 산출물은 Best Question 1개가 아니라 **High-Value Question Portfolio**(Pareto frontier 유지, 단일 scalar 압축 금지).

---

## 2. 인지적 독립성 — 에이전트 수보다 중요 (전원 합의, 실증 최다)

### 실증 근거

- 동질 에이전트 debate는 단순 majority voting보다 못할 수 있음 (Demystifying MAD, 2026)
- 에이전트 수 증가 ≠ 다양성 증가; 밀집 통신 구조가 조기 수렴 가속 (Diversity Collapse, 2026)
- 동일 계열 모델 복제 시 추론 표현 고유사성 (Representational Collapse)
- novelty 명시 지시 + 자기성찰 + 문헌 검색을 다 해도 인간 수준 탐험 범위 미달 — **프롬프트로는 못 푼다** (Agent 4 강조)

### 원칙: Independent First, Interact Later

독립 탐사 → Diversity Check → 통제된 교차수분. 처음부터 컨텍스트를 공유하면 동조화된다.

### 4차원 이종성 (Agent 1 프레임, 타 보고와 정합)

| 차원 | 내용 | 구현 |
|---|---|---|
| Model Diversity | 다른 벤더·아키텍처·훈련분포 | 페르소나 분리보다 실효적. PAO 이종 LWAR 병렬 구조와 직결 |
| Epistemic Diversity | 같은 자료에서 다른 것을 찾음 | Contradiction Hunter, Assumption Breaker, Boundary Explorer 등 역할군 |
| Evidence Diversity | 처음부터 다른 문헌 배분 | 논문/특허/코드/뉴스/실패사례/규제/역사 소스별 분리 후 비교 |
| Objective Diversity | reward 자체가 다름 | 중요도 최대화 vs 상식 반증 vs 비용 대비 정보량 등 목표함수 분리 |

### 수렴 제어기

임베딩 유사도 상승 시 강제 발산(Adversarial Perturbation), 발산 단계(합의 금지)와 정제 단계(합의 유도)의 명시적 분리. Agent 4는 이것이 **HELIX explore/exploit 이중나선의 재사용 지점**이라고 지목.

---

## 3. Question Object — 문자열이 아닌 구조화 객체 (전원 합의)

자유문 질문은 검증·중복제거·랭킹이 불가능. FirstResearch의 Research Question Certificate(certificate 제거 ablation에서 평가 성능 대폭 악화)가 실증 근거.

최소 스키마: `{질문, 대상 개념, 전제/가정, 미지수, 근거·출처, 반론, 반증 조건(falsifier), 최소 결정적 테스트, 예상 정보이득, 비용, 다음 액션, 계보(parents/children/operator), 상태}`. Agent 8의 Inquiry Card YAML이 가장 완전한 예시. PGF/Gantree로 스키마를 정의하면 기존 자산 재사용 가능.

---

## 4. Question Graph + 계보 추적 (전원 합의)

핵심 데이터 구조는 Chat Log가 아니라 그래프: `Knowledge Graph → Claim Graph(supports/contradicts/unexplained/gap) → Question Graph`. 질문은 lineage를 가진 영속 노드(derived_from, operator, parent, contradicts, evidence, descendants, status).

- Provenance 없이는 시스템 개선도 사후 가치검증도 불가능 (Agent 4·8)
- DORMANT 질문의 재활성화: 환경 변화(신기술 등장) 시 휴면 질문 재평가 → **Inquiry Observatory**로 진화 (Agent 1)
- 장기 해자는 모델이 아니라 질문 그래프 + 평가 결과 + 후속 실행 데이터 (Agent 5·7)

---

## 5. Question Operators / Question Grammar

"새 질문을 만들어라"는 학습 데이터 패턴으로 회귀한다. 질문 공간을 변환하는 연산자를 명시적으로 정의:

Contradiction, Assumption Inversion, Boundary, Scaling, Cross-domain, Missing Variable, Causal, Measurement, Counterfactual, Second-order, Adversarial, Regime Change (Agent 1) = 질문 렌즈 8종 (Agent 5) = 질문 유형 7분류 (Agent 8). 명칭만 다르고 동일 개념 — **질문 문법이 제품의 핵심 IP**.

발전형: AI가 새 operator 자체를 발견 → 질문 생성 시스템에서 질문 생성 방법을 진화시키는 시스템으로.

---

## 6. Unknown Detector — 차별화 모듈 (Agent 1 고유, 타 보고의 gap mining과 정합)

질문 생성 전에 "무엇을 모르는가"부터 탐지. Unknown 10분류: Known Unknown, Contradictory, Hidden Assumption, Measurement, Causal, Boundary, Cross-domain Gap, Temporal, Emergent, **Unknown Unknown Candidate**(그래프의 비정상 단절·공백 탐지). 이 지점부터 LLM prompting보다 Knowledge Graph + Graph Algorithm + LLM reasoning 결합이 우세.

전제 조건: 모든 지식에 불확실성 메타데이터(confidence, evidence strength, temporal validity, contradiction flag, unknown flag) 부착 — 이것이 있어야 "모르는 것"이 질문으로 전환된다 (Agent 8).

---

## 7. 평가 시스템 — 진짜 기술적 해자 (전원 합의, 최대 리스크)

### 실증 경고

- **Novelty Mirage**: LLM judge는 AI 생성 질문을 과대평가 (RQ-Bench 2026)
- **HindSight**: LLM judge가 못 가른 차이를 30개월 time-split 실측이 2.5배로 갈랐고, LLM 고평가 novelty와 실제 미래 연구 일치도는 음의 상관
- **Style Bias**: 내용 동일해도 표현만 바꾸면 평가가 달라짐 → 심사 시 모델명·원문 스타일 은닉, 표준화 표현으로 변환 후 평가

### 2단계 구조: Hard Gates → Value Ranking

Hard Gates(통과 필수): Grounded / Non-duplicate / Clearly formulated / Answer path exists / Evidence traceable / Falsifiable / Minimal decisive test possible.

Value Dimensions(공통 축, 표기만 상이): Novelty(외부 그라운딩 필수 — 기존 질문 코퍼스 임베딩 거리 + 인용그래프 비정형 조합 탐지), Impact/Leverage, Testability, Actionability, Evidence Grounding, Feasibility, Safety, Diversity Contribution, Robustness.

### Actionability Gate (Agent 2·4 공통)

질문마다 최소 실행계획(실험 프로토콜/시뮬레이션 코드) 1개를 자동 생성시키고, 생성 실패 질문은 기각. 철학적 질문과 연구 질문을 가르는 실용 기준.

### 현실적 경로 (Agent 4)

완전 자동평가를 초기 목표로 삼지 말 것. **AI 토너먼트 → 인간 최종 선별** 하이브리드로 시작, 선별 로그를 평가기 학습 데이터로 축적. 장기적으로 reward model이 "AI가 생각하는 좋은 질문" → "실제 가치가 있었던 질문"으로 이동.

---

## 8. Dissent Preservation — 합의는 종료조건이 아니다 (전원 합의)

일반 MAS: 토론 → Consensus. InquiryFoundry: 불일치 → Disagreement Map → "왜 불일치하는가?" → **새 질문**. Persistent disagreement = inquiry source. 구현: minority report, dissent log, high-risk high-novelty bucket, Confidence-Calibrated Debate(다수결의 폭정 방지), DEAR식 상호참조 동적 조절.

Socratic Synthesizer(Agent 2): 양자택일 대신 상충 자체를 포착하는 고차원 질문 재구성.

---

## 9. 오케스트레이션 아키텍처 (수렴된 표준 패턴)

**Supervisor(중앙 오케스트레이터) + 병렬 전문가 + 심사 루프**로 시작 (Co-Scientist 패턴; 자유형 스웜은 금지). 공통 파이프라인:

```text
Inquiry Brief 정규화 (대상·목표·제약·금지 전제·성공 기준)
→ Knowledge Mapping / 지식 지형화
→ Assumption Mining (전제 해체)
→ Multi-Agent 독립 발산 생성
→ Cross-Examination (구조화된 반론 6유형: 증거/논리/전제/대안/이해관계/실행)
→ Prior-Art & Novelty Check (외부 그라운딩)
→ Scoring & Clustering (Hard Gate → Ranking)
→ Question Card 생성
→ Human Review (승인 관문)
→ Action Packaging (실험/파일럿/의사결정 전환)
→ Feedback Memory (결과를 다음 생성에 반영)
```

핵심 역할군(보고 간 교집합): Orchestrator/Director, Knowledge Curator/Evidence Scout, Assumption Auditor, Cross-Domain Analogist, Contrarian/Red Team, Futurist/Scenario, Feasibility/Falsifiability Engineer, Question Composer, Judge Ensemble(생성 모델과 분리), Ethicist/Safety, Outcome Learner, Human Facilitator.

운영 요건: 이벤트 소싱 실행 로그, 버전 관리 블랙보드, typed message schema + MCP/A2A 어댑터, 메모리 4분리(세션/장기/증거/실행), 질문 ID 단위 관측성(모델·프롬프트 버전·비용·지연·점수 변화), 타임아웃·재시도·서킷 브레이커.

---

## 10. Meta-Inquiry — 질문의 질문

1차 질문의 abstraction level이 최적이라는 보장 없음. `Q → Q(Q) → Q' → Q''` = Question Refinement Tree. "왜 우리는 이 문제를 이렇게 정의했는가?"를 주기적으로 시스템 자신에게도 적용(자기 개선).

---

## 11. 실패 모드와 대응 (통합표)

| 실패 모드 | 대응 |
|---|---|
| 다양성 붕괴·조기 수렴 | 진짜 이종 모델, 독립 생성 후 토론, 유사도 감시 + 강제 발산, 온도 스케줄 |
| 가짜 신규성(pseudo-novelty) | 외부 그라운딩 novelty(prior art search, 임베딩 거리), 지식그래프 대조 |
| 환각 기반 질문 | evidence citation 강제, grounding score, Formal KG + 기호적 검증기 |
| 의사 지적 질문(검증 불가 말장난) | Actionable Protocol Generator Test — 실행계획 생성 실패 시 기각 |
| 질문 공간 폭발 | Impact-Guided Tree Search(MCTS 변형), 선택적 토론 트리거 |
| LLM-as-Judge 편향(novelty mirage, style bias) | 블라인드 심사, 표준화 표현 변환, 인간 하이브리드, time-split 사후검증 |
| 합의 편향 | dissent preservation, devil's advocate 필수화 |
| 기억 부재(질문 반복) | Inquiry Memory, 실패 패턴 학습 |
| 인간 배제·블랙박스화 | human-in-the-loop 최종화, provenance, reasoning trace, audit log |
| 보안 | prompt injection·오염 문서·dual-use 질문 방어, safety gate |

---

## 12. 기존 자산 매핑 (Agent 4·5·8 공통 지적)

| InquiryFoundry 요구 | 보유 자산 |
|---|---|
| 이종 런타임 병렬 생성 계층 | PAO 이종 LWAR 병렬 실행 + 중복제거·통합 — 원리 일치, 직결 가능. 단일모델-다역할 학술 시스템 대비 구조적 우위 |
| 수렴 제어기(explore/exploit) | HELIX 이중나선 구조 재사용 |
| 질문 스키마·설계 명세 | PGF/Gantree로 Question Object·파이프라인 정의 |
| 분산 확장 | SeAAI/멀티에이전트 생태계 인프라 |

**신규 개발이 필요한 3가지** (Agent 4): ① 질문 스키마, ② 외부 그라운딩 novelty 측정, ③ 수렴 제어기.

---

## 13. MVP 로드맵 (수렴안)

**Phase 1 (0~3개월, 개념 검증)**: 단일 도메인, 5~7 고정 역할 에이전트(Knowledge Curator, Assumption Auditor, Contrarian, Feasibility Engineer, Question Composer), 기본 RAG, 질문 카드 100개 생성 → 전문가 10개 채택 폐루프. 성공 기준: "생각해 본 적 없다" 비율, 실험 연결 비율.

**Phase 2 (3~9개월, 검증 강화)**: prior art search, 중복 탐지, KG 초안, safety filter, dissent log, human review dashboard. 성공 기준: false novelty 감소, 검토 시간 감소.

**Phase 3 (9~18개월, 폐루프화)**: inquiry memory, 실험 결과 ingestion, lineage, feedback re-ranking, 질문 포트폴리오 대시보드(중요도 × 불확실성 × 검증비용 × 시급성).

첫 웨지(Agent 5): 범용 서비스가 아니라 질문의 경제 가치가 명확한 좁은 도메인 — AI 에이전트/양자-AI/산업 자동화 연구용 **Frontier Inquiry Copilot**이 배경상 자연스러움.

핵심 KPI: Expert Novelty Rate, Actionable Question Rate, Experiment Conversion Rate, False Novelty Rate, Time-to-Question, Dissent Quality, Decision-Change Rate, 질문당 비용·지연.

---

## 14. 전략 예측 (교차 합의)

1. **답변은 상품화, 질문은 희소 자원화**: 병목이 execution → problem selection으로 이동. 차별화는 생성이 아니라 필터링·평가 (6~18개월 내 승부).
2. **Inquiry Base가 자산이 됨**: 조직은 Knowledge Base에 더해 질문 포트폴리오·질문 그래프를 관리. "inquiry marketplace" 개념 가능.
3. **기업 고객은 창의성보다 근거·감사성·재현성을 구매**: provenance와 관측성은 부가기능이 아니라 코어.
4. **다양성 붕괴 문제를 구조적으로 푼 시스템은 선행 사례가 거의 없는 공백 지대** — 이종 런타임 실환경 보유가 논문들이 못 하는 실험을 가능하게 함.
5. AgentPanel과의 결정적 차이: 그들은 사람이 질문을 넣고 AI가 탐색, InquiryFoundry는 **"무엇을 질문해야 하는가" 자체를 발견** — 한 단계 앞.

---

## 15. 결론 — 우선 명세 3종

전 보고를 관통하는 최우선 착수 항목:

1. **Question Object Schema** (Certificate 수준 구조화, PGF로 정의)
2. **Question Operators / Grammar** (질문 공간 변환 연산자 세트)
3. **Diversity·Value Metric + 외부 그라운딩 평가 파이프라인** (Hard Gates + Pareto Portfolio)

이 셋이 명세되면 멀티모델 오케스트레이션 구현(PAO+HELIX 재사용)은 선명해진다. 시스템 철학은 한 문장으로:

> **Do not make multiple AIs agree. Make their disagreements reveal what humanity has not yet thought to ask.**

7단 골격: Independent Exploration → Unknown Mining → Question Evolution → Adversarial Validation → Quality-Diversity Selection → Question Graph → Outcome Feedback.
