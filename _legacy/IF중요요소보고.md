# InquiryFoundry: 다종의 AI 에이전트가 서로 다른 지식·관점·반론을 교차시켜, 검증 가능하고 행동 가능한 새로운 질문을 생산하는 Inquiry Intelligence System.

AI 문명시대를 맞아 대답보다 질문이 중요해진 시대가 도래했다. 
기존에 없던 개념, 기술, 현상들에 대해서 기존에 없던 질문은 가치가 큰 혁신을 가져올 가능성이 있다.
다종의 멀티에이전트 오케스트레이션시스템을 이용해서 질문을 생산하는 시스템을 만들려고 한다.
이 시스템에 중요한 요소들이 무엇일지를 정보를 수집하고, 분석, 예측해서 제시해줘.

# ===========================================
# AI Agent 1

정욱님이 정의한 **InquiryFoundry**는 단순한 “Question Generator”보다 훨씬 큰 개념으로 잡는 것이 맞습니다.

> **InquiryFoundry = 여러 AI가 지식공간을 탐사하고, 서로 다른 인식·가정·반론을 충돌시키며, 아직 명확하게 제기되지 않은 ‘가치 있는 미지(Unknown)’를 찾아내고, 그것을 검증 가능하고 행동 가능한 Question Object로 변환하는 시스템**

2026년 8월 13일 현재 관련 연구들을 보면, 이 방향을 구성하는 개별 기술들은 상당히 나타났지만 **질문 자체를 최종 생산물로 두고, 이질적 모델·다양성 유지·질문 진화·외부 검증·정보가치 평가를 하나의 시스템으로 통합하는 구조**는 아직 초기 단계에 가깝습니다. 특히 최근 연구들은 “답을 잘하는 AI ≠ 필요한 질문을 잘 찾는 AI”라는 점을 분명히 보여주고 있습니다. ICML 2025의 Active Reasoning 연구에서는 완전한 정보를 주면 문제를 해결할 수 있는 모델도, 빠진 정보를 알아내기 위해 **무엇을 물어야 하는가**에서는 크게 어려움을 보였습니다. ([arXiv][1])

---

# 1. 먼저 InquiryFoundry의 최적화 목표를 바꿔야 한다

일반적인 생성 시스템은 대체로

**Prompt → Candidate → Evaluate → Best Answer**

를 최적화합니다.

InquiryFoundry는 달라야 합니다.

**Knowledge → Unknown Detection → Question Space Exploration → Question Validation → Inquiry Portfolio**

즉 최종 목적함수는

> **“얼마나 참신한 문장을 만들었는가?”가 아니라
> “이 질문에 답했을 때 우리의 세계모델이 얼마나 크게 바뀌는가?”**

여야 합니다.

AutoDiscovery는 이를 뒷받침하는 흥미로운 방향을 보여줍니다. 이 연구는 단순한 다양성이나 인간이 느끼는 흥미로움 대신 **Bayesian Surprise**, 즉 관측 전후의 믿음 변화량을 탐색 기준으로 사용했습니다. 21개 실제 데이터셋에서 고정된 탐색 비용으로 기존 방식보다 5~29% 더 많은 surprising discoveries를 발견했고, 인간 전문가 평가에서도 시스템이 surprising하다고 판단한 발견의 약 3분의 2가 전문가에게도 놀라운 것으로 평가됐습니다. ([arXiv][2])

따라서 InquiryFoundry의 가장 중요한 기본 개념은 다음이라고 봅니다.

[
Question\ Value \neq Novelty
]

오히려

[
Question\ Value \approx
Expected\ Knowledge\ Change
\times
Importance
\times
Answerability
]

입니다.

---

# 2. 가장 중요한 요소는 “에이전트 숫자”가 아니라 **인지적 독립성**

멀티에이전트라 하면 흔히 10개의 AI를 놓고 서로 토론시키는 방식을 생각합니다.

그런데 최근 연구는 이 접근의 약점을 상당히 명확하게 보여줍니다.

2026년 *Demystifying Multi-Agent Debate* 연구에서는 동질적인 에이전트가 동일한 방식으로 belief update를 하면 vanilla debate가 단순 majority voting보다 못할 수도 있으며, 성능 향상을 위해 특히 **초기 관점의 다양성**과 **신뢰도에 대한 명시적인 전달**이 중요하다고 분석했습니다. ([arXiv][3])

더 직접적인 연구도 있습니다. *Diversity Collapse in Multi-Agent LLM Systems*에서는 에이전트 수가 증가한다고 탐색 다양성이 계속 증가하지 않았으며, 오히려 밀집된 통신 구조가 조기 수렴을 가속할 수 있다고 보고했습니다. 강력하게 alignment된 모델일수록 각 응답 품질은 높지만 추가 샘플의 다양성 증가량은 감소하는 현상도 관찰됐습니다. ([arXiv][4])

그리고 representational collapse 연구에서는 동일 계열 모델을 여러 에이전트로 복제했을 때 추론 표현의 높은 유사성이 관찰됐습니다. ([arXiv][5])

따라서 InquiryFoundry에는 아주 중요한 원칙이 필요합니다.

### **Independent First, Interact Later.**

처음부터 서로의 생각을 보여주면 안 됩니다.

예를 들어:

```text
Knowledge
   │
   ├── AI-A ── independent exploration
   ├── AI-B ── independent exploration
   ├── AI-C ── independent exploration
   ├── AI-D ── independent exploration
   └── AI-E ── independent exploration
          │
          ▼
    Diversity Check
          │
          ▼
    Controlled Cross-Pollination
```

이렇게 해야 합니다.

---

# 3. “다종 AI”의 의미도 4차원으로 확장할 필요가 있다

InquiryFoundry에서 heterogeneous는 단순히

GPT + Gemini + Claude + Grok + DeepSeek

정도로 끝나면 안 됩니다.

제가 보기에는 최소한 **4종류의 독립성**을 의도적으로 만들어야 합니다.

### ① Model Diversity

서로 다른 학습 데이터, post-training, reasoning architecture, tool environment를 가진 모델을 사용합니다.

이는 진짜 다종 모델 오케스트레이션의 장점입니다. 동일 모델에 “너는 비판가다”, “너는 과학자다”라는 persona만 바꾸는 것보다 구조적인 다양성이 큽니다. 최근 과학 창의성 연구에서도 동일 모델 복제 기반 multi-LLM 시스템이 shared bias와 diversity 제한을 가질 수 있다는 문제가 제기됐습니다. ([arXiv][6])

### ② Epistemic Diversity

같은 자료를 보더라도 무엇을 찾는지가 달라야 합니다.

예를 들어:

```text
Contradiction Hunter
Assumption Breaker
Boundary Explorer
Causal Investigator
Anomaly Hunter
Cross-domain Analogist
Counterfactual Explorer
Measurement Skeptic
Failure Analyst
Second-order Effect Analyst
```

같은 역할입니다.

### ③ Evidence Diversity

더 중요한 방법입니다.

**각 AI에게 처음부터 동일한 문헌을 주지 않습니다.**

예:

```text
AI-A → 논문
AI-B → 특허
AI-C → GitHub / 실제 구현
AI-D → 산업 뉴스
AI-E → 실패 사례
AI-F → 규제 / 정책
AI-G → 역사적 사례
```

그런 다음 서로 비교합니다.

Graph2Idea 연구 역시 평면적인 텍스트 묶음 대신 논문 간의 problem-method-mechanism-finding 관계를 knowledge graph로 구성했을 때 생성 아이디어의 novelty, quality, feasibility가 개선됐다고 보고했습니다. ([arXiv][7])

### ④ Objective Diversity

마지막으로 reward 자체도 달라야 합니다.

한 AI는

> “가장 중요한 질문”

을 찾고,

다른 AI는

> “현재 상식이 틀렸을 가능성을 가장 크게 드러내는 질문”

또 다른 AI는

> “답을 얻는 비용 대비 정보량이 가장 큰 질문”

을 찾도록 합니다.

이것이 **Functional Heterogeneity**입니다.

---

# 4. InquiryFoundry에는 반드시 **Question Operators**가 필요하다

LLM에게 단순히

> “새롭고 중요한 질문을 만들어라.”

라고 하면 결국 학습 데이터에서 자주 등장했던 질문 패턴으로 회귀할 가능성이 큽니다.

대신 질문 공간을 의도적으로 변환시키는 **Inquiry Operators**를 정의하는 것이 좋습니다.

예를 들어 한 주장 A가 있을 때:

| Operator             | 생성되는 질문                         |
| -------------------- | ------------------------------- |
| Contradiction        | A와 B가 동시에 사실일 수 없는 이유는 무엇인가?    |
| Assumption inversion | A의 핵심 가정이 거짓이라면 무엇이 발생하는가?      |
| Boundary             | A는 어느 조건에서 더 이상 성립하지 않는가?       |
| Scaling              | A가 1,000배 커지면 어떤 새로운 현상이 나타나는가? |
| Cross-domain         | 다른 분야의 원리 X를 A에 적용하면 무엇이 가능한가?  |
| Missing variable     | 현재 모델이 빠뜨리고 있는 변수가 있는가?         |
| Causal               | A와 B의 상관관계를 만드는 실제 원인은 무엇인가?    |
| Measurement          | 우리가 A를 잘못 측정하고 있는 것은 아닌가?       |
| Counterfactual       | A가 존재하지 않았다면 B는 발생했을까?          |
| Second-order         | A가 성공했을 때 발생하는 2차 효과는 무엇인가?     |
| Adversarial          | A를 의도적으로 실패시키는 가장 쉬운 방법은 무엇인가?  |
| Regime change        | 환경이 변하면 기존 법칙이 언제 역전되는가?        |

여기에 AI가 새로운 operator 자체를 발견하도록 할 수도 있습니다.

이것은 상당히 중요합니다.

**질문을 생성하는 시스템에서 → 질문 생성 방법 자체를 진화시키는 시스템**으로 넘어가기 때문입니다.

---

# 5. 핵심 데이터 구조는 Chat Log가 아니라 **Question Graph**여야 한다

이 부분은 InquiryFoundry의 기술적 핵심이 될 가능성이 높습니다.

최근 Evolving Idea Graph 연구는 multi-agent ideation을 단순한 대화 로그로 유지하면 어떤 약점이 남아 있고 어떤 수정이 이루어졌는지 추적하기 어렵다고 지적하고, 주장들을 node로, support/conflict 관계를 edge로 만든 evolving graph를 사용했습니다. 이 방식은 자동 평가뿐 아니라 blind expert 평가에서도 비교 시스템들을 앞섰습니다. ([arXiv][8])

InquiryFoundry 역시 다음 형태가 적합합니다.

```text
Knowledge Graph
      │
      ▼
Claim Graph
      │
      ├── supports
      ├── contradicts
      ├── unexplained
      ├── uncertain
      └── disconnected
              │
              ▼
          Question Graph
```

Question Graph에서는 질문 자체가 영속 객체가 됩니다.

예를 들면:

```text
Q173
 ├─ derived_from: Claim-19, Claim-72
 ├─ operator: Assumption-Inversion
 ├─ parent: Q104
 ├─ contradicts: Q151
 ├─ evidence: E13,E91,E142
 ├─ descendants: Q188,Q201
 ├─ status: OPEN
 └─ confidence: ...
```

질문도 **계보(lineage)**를 가지는 겁니다.

---

# 6. Question을 문자열이 아니라 **Question Object**로 만들어야 한다

이것은 매우 강하게 권합니다.

최근 FirstResearch는 과학적 질문을 단순 문장으로 출력하는 대신 **Research Question Certificate**를 만들고, primitive definitions, assumptions, mechanism, tension, falsifiable hypothesis, minimal test, failure-update rule 등을 기록하게 했습니다. 아직 10개 주제와 LLM judge 중심의 예비 연구라는 한계는 있지만, certificate를 제거한 ablation에서 평가 성능이 크게 악화돼 구조화된 질문 표현의 가능성을 보여줍니다. ([arXiv][9])

InquiryFoundry에서는 이것을 더 확장할 수 있습니다.

### Inquiry Question Object

```yaml
question_id:
question:
question_class:

why_this_question_matters:

evidence:
known_facts:
unknowns:
contradictions:

assumptions:
mechanism:

competing_explanations:

novelty_evidence:
closest_existing_questions:

expected_information_gain:

possible_answers:
answer_consequences:

minimal_test:
falsifier:

required_tools:
estimated_cost:

impact:
feasibility:
urgency:

minority_arguments:
unresolved_objections:

parents:
children:
generation_operator:

created_at:
last_verified_at:
status:
```

그러면 질문이 단순 텍스트가 아니라

> **추적·수정·실험·재검증 가능한 지식 객체**

가 됩니다.

HEP 연구에서도 hypothesis를 persistent object로 만들고 evidence에 따라 belief를 업데이트하며 append-only history를 유지하는 방식의 중요성이 제기되고 있습니다. ([arXiv][10])

---

# 7. 질문의 평가함수가 InquiryFoundry의 진짜 기술적 해자다

여기에서 프로젝트의 성패가 결정될 가능성이 큽니다.

단순히

```text
Novelty = 9
Impact = 8
Feasibility = 7
```

을 LLM에게 물으면 위험합니다.

2026년 RQ-Bench 연구는 LLM judge가 AI 생성 연구질문을 실제보다 과도하게 novel하다고 평가하는 **novelty mirage**를 발견했습니다. 인간 전문가들은 반대로 기존 논문 저자들이 실제로 제기했던 질문들을 더 선호하는 경향을 보였습니다. ([arXiv][11])

HindSight에서는 더 흥미로운 결과가 나왔습니다. LLM judge는 retrieval 기반과 vanilla idea-generation 사이에 유의미한 차이를 거의 찾지 못했지만, 이후 30개월간 실제로 출판된 연구와 비교하는 time-split 평가에서는 retrieval 기반 아이디어의 점수가 약 2.5배 높았습니다. 게다가 LLM이 높게 평가한 novelty와 미래 연구 일치도 사이에는 음의 상관도 관찰됐습니다. ([arXiv][12])

그래서 저는 InquiryFoundry 평가를 **두 단계**로 나누는 것을 권합니다.

### Hard Gates

먼저 반드시 통과해야 하는 조건입니다.

```text
Grounded?
Non-duplicate?
Clearly formulated?
Relevant unknown exists?
Answer path exists?
Evidence traceable?
```

과학적 질문이라면 추가로

```text
Falsifiable?
Measurable?
Minimal decisive test possible?
```

을 봅니다.

그 다음에야 Ranking을 합니다.

### Value Dimensions

제가 초기 버전에서 넣을 핵심 변수는 다음과 같습니다.

[
IV(Q)=f(
IG,,
N,,
G,,
D,,
I,,
F,,
A,,
U,,
R
)
]

여기서

* **IG — Expected Information Gain:** 답을 알았을 때 불확실성이 얼마나 감소하는가
* **N — Verified Novelty:** 검색 결과 실제 기존 질문과 얼마나 다른가
* **G — Grounding:** 근거 자료와 얼마나 연결되어 있는가
* **D — Diversity Contribution:** 기존 질문 포트폴리오에 없는 방향인가
* **I — Impact:** 답이 밝혀지면 얼마나 큰 변화가 생기는가
* **F — Feasibility:** 현실적으로 답을 얻을 수 있는가
* **A — Actionability:** 다음 행동으로 연결되는가
* **U — Uncertainty:** 실제 미지인가
* **R — Robustness:** 반론을 견디는가

입니다.

초기부터 하나의 scalar로 압축하기보다는 **Pareto frontier**를 유지하는 것을 권합니다.

왜냐하면

> 매우 새롭지만 실험비가 큰 질문

과

> 새로움은 약하지만 내일 바로 검증 가능한 질문

을 동일한 숫자로 순위를 매기는 것은 정보 손실이 크기 때문입니다.

IDEAgent도 최근 scientific ideation을 **Quality + Diversity의 동시 최적화 문제**로 정의하고, 일정 quality threshold를 통과하면서 서로 다른 아이디어의 최대 집합을 평가하는 Yield metric을 제안했습니다. 32개 주제에서 가장 강한 비교 방법보다 3.89배 높은 Yield를 보고했습니다. ([arXiv][13])

InquiryFoundry 역시 **Best Question 1개가 아니라 High-Value Question Portfolio**를 만드는 것이 더 맞습니다.

---

# 8. 따라서 추천하는 전체 InquiryFoundry Loop

제가 현재 연구들을 종합해서 설계한다면 이런 구조가 됩니다.

```text
                 ┌─────────────────────┐
                 │   Inquiry Mission   │
                 └─────────┬───────────┘
                           ↓
                 Knowledge Acquisition
                           ↓
                Epistemic Knowledge Graph
                           ↓
           ┌──────── Independent Exploration ────────┐
           │          │          │          │        │
        Model A    Model B    Model C    Model D  Model E
        Papers     Patents     Code       News    History
           │          │          │          │        │
           └───────────────┬─────────────────────────┘
                           ↓
                  Unknown / Gap Mining
                           ↓
                     Question Seeds
                           ↓
                 Diversity Measurement
                           ↓
              ┌────── Question Evolution ──────┐
              │                                 │
          Mutation                           Merge
              │                                 │
      Assumption inversion             Cross-domain fusion
      Counterfactual                   Contradiction synthesis
      Boundary shift                   Analogy transfer
              └──────────────┬──────────────────┘
                             ↓
                   Controlled Debate
                             ↓
            Skeptic / Falsifier / Red Team
                             ↓
                  External Verification
               Papers / Web / Code / Data
                             ↓
                  Question Certificate
                             ↓
               Quality-Diversity Archive
                             ↓
        ┌────────────────────┼───────────────────┐
        ↓                    ↓                   ↓
     Research             Experiment           Monitor
        ↓                    ↓                   ↓
              Evidence / Outcome Feedback
                             ↓
                       Question Graph
                             ↺
```

이 구조는 Co-Scientist의 generate–critique–refine 및 tournament evolution, EvoSci의 selection–crossover–mutation 방식, QD 탐색, graph 기반 ideation의 강점을 **질문 생성 문제에 맞게 재배치한 합성 설계**입니다. Co-Scientist는 실제 biomedical applications에서도 생성한 가설 일부를 실험적으로 검증했습니다. ([arXiv][14])

---

# 9. 매우 중요한 기능: **Dissent Preservation**

InquiryFoundry에서는 consensus가 목표여서는 안 됩니다.

일반적인 multi-agent 시스템은

```text
A 주장
B 주장
C 주장
    ↓
Debate
    ↓
Consensus
```

를 지향합니다.

InquiryFoundry에서는 오히려

```text
A
B
C
 ↓
Disagreement Map
 ↓
Why do they disagree?
 ↓
New Question
```

이어야 합니다.

즉

> **불일치를 제거하지 말고 질문으로 변환해야 합니다.**

2026년 8월 공개된 DEAR 연구도 multi-agent debate에서 minority가 majority를 따라가는 blind conformity 문제를 지적하며, 상호참조 관계 자체를 동적으로 조절하는 방식을 제안했습니다. ([arXiv][15])

따라서 InquiryFoundry에서

**Consensus = 종료조건**

이 아니라

**Persistent disagreement = 새로운 inquiry source**

가 되어야 합니다.

이 차이가 굉장히 중요합니다.

---

# 10. 제가 추가하고 싶은 핵심 모듈: **Unknown Detector**

기존 시스템과 InquiryFoundry를 가장 크게 차별화할 수 있는 부분입니다.

AI에게 질문을 만들라고 하는 것이 아니라 먼저

> **“우리가 무엇을 모르는지 찾아라.”**

라고 합니다.

Unknown을 다음과 같이 분류할 수 있습니다.

```text
Known Unknown
    우리가 모른다는 것을 알고 있음

Contradictory Unknown
    서로 충돌하는 지식이 존재

Hidden Assumption
    사실처럼 취급하지만 검증되지 않은 가정

Measurement Unknown
    측정 방법 자체가 불완전

Causal Unknown
    현상은 알지만 원인을 모름

Boundary Unknown
    법칙이 어디까지 성립하는지 모름

Cross-domain Gap
    분야 A와 B 사이의 연결이 탐색되지 않음

Temporal Unknown
    환경 변화로 과거 지식이 더 이상 유효한지 모름

Emergent Unknown
    새로운 기술 때문에 과거에는 존재하지 않았던 문제

Unknown Unknown Candidate
    기존 지식 구조의 비정상적 단절이나 공백
```

마지막 **Unknown Unknown Candidate**가 특히 흥미롭습니다.

Graph의 비정상적인 구조를 탐색해

```text
A ─ B ─ C

D ─ E

F ─ G
```

왜 C와 D 사이에는 연결이 없는가?

왜 A 분야에서는 X를 사용하지만 F 분야에서는 사용하지 않는가?

같은 질문을 자동 생성할 수 있습니다.

이 지점부터는 단순 LLM prompting보다 **Knowledge Graph + Graph Algorithms + LLM reasoning**의 결합이 강해질 것입니다.

---

# 11. “질문의 질문”도 생성하게 해야 한다

InquiryFoundry가 충분히 발전하면 1차 질문만 생성해서는 안 됩니다.

예를 들어:

> “AI 데이터센터의 물 사용량을 줄이는 가장 좋은 방법은 무엇인가?”

라는 질문이 나왔다고 합시다.

Meta Inquiry Agent는 다시 묻습니다.

> 왜 우리는 물 사용량을 최소화해야 한다고 정의했는가?

> 데이터센터 위치 자체를 바꾸는 질문이 더 상위 질문 아닌가?

> 물 소비가 아니라 전체 ecological opportunity cost를 묻는 것이 맞지 않는가?

즉

[
Q \rightarrow Q(Q)
]

를 수행합니다.

그리고 또 가능해집니다.

[
Q \rightarrow Q' \rightarrow Q'' \rightarrow Q'''
]

이것은 **Question Refinement Tree**가 됩니다.

가장 가치 있는 질문이 반드시 최초 질문과 같은 abstraction level에 있다는 보장은 없습니다.

---

# 12. InquiryFoundry의 평가 시스템에는 장기 피드백이 필요하다

아마 이것이 장기적으로 가장 큰 자산이 될 겁니다.

질문이 나온 순간에는 그 질문이 좋은지 정확히 알 수 없습니다.

따라서 기록해야 합니다.

```text
Question generated
       ↓
Selected?
       ↓
Investigated?
       ↓
Produced useful evidence?
       ↓
Changed decision?
       ↓
Created invention?
       ↓
Generated another valuable question?
```

몇 달 또는 몇 년 뒤

> 과거 어떤 종류의 질문이 실제 가치로 이어졌는가?

를 학습합니다.

그러면 InquiryFoundry의 reward model은

**AI가 생각하는 좋은 질문**

에서

**실제로 가치가 있었던 질문**

으로 이동합니다.

이 점에서 HindSight처럼 과거 시점의 정보만 모델에게 제공하고 이후 실제 연구 발전과 비교하는 temporal evaluation이 특히 유용한 benchmark가 될 수 있습니다. ([arXiv][12])

---

# 13. 실패 가능성이 높은 설계

반대로 다음 구조는 피하는 편이 좋다고 판단합니다.

```text
10 AI
 ↓
같은 자료
 ↓
같은 질문
 ↓
자유 토론
 ↓
다수결
 ↓
Judge AI
 ↓
Top 10 Questions
```

겉보기에는 멀티에이전트지만 실제로는

**Parallel Sampling + Consensus Filter**

에 가깝습니다.

다음 문제가 발생할 가능성이 큽니다.

* model monoculture
* diversity collapse
* authority bias
* majority conformity
* semantic duplication
* pseudo-novelty
* LLM-as-Judge bias
* polished-language bias
* early convergence
* source echo
* reward hacking

실제로 2026년 LLM-as-Judge 연구에서는 과학 아이디어의 **내용은 그대로인데 표현 방식이 달라지는 것만으로 평가가 달라지는 style bias**도 보고됐습니다. ([arXiv][16])

따라서 심사 단계에서는 모델명과 원문 스타일을 숨기고, 가능하면 질문을 표준화된 structured representation으로 변환한 뒤 평가하는 것이 좋습니다.

---

# 14. 기존 연구와 InquiryFoundry의 위치

현재 조사한 시스템을 놓으면 대략 다음처럼 보입니다.

| System               | 주요 목적                                     |
| -------------------- | ----------------------------------------- |
| AI Scientist-v2      | 연구 수행 및 논문 생성                             |
| Co-Scientist         | 가설 생성·경쟁·진화                               |
| AutoDiscovery        | surprise 기반 open-ended hypothesis 탐색      |
| IDEAgent             | Quality-Diversity 기반 아이디어 탐색              |
| Evolving Idea Graphs | 그래프 기반 아이디어 진화                            |
| FirstResearch        | auditable research question 생성            |
| AgentPanel           | 이질적 AI들의 비동기 과학 토론                        |
| **InquiryFoundry**   | **미지 탐색 → 질문 생성 → 반론 → 검증 → 진화 → 포트폴리오화** |

AI Scientist-v2는 hypothesis–experiment–analysis–paper까지 자동화했고, Co-Scientist는 multi-agent hypothesis tournament를 구현했습니다. ([arXiv][17])

특히 2026년 8월 공개된 AgentPanel은 정욱님 아이디어와 가까운 신호입니다. heterogeneous agents가 forum 형태로 비동기적으로 과학 문제를 토론하게 했고, 2026년 3~7월 실제 시스템에서 1,508개 scientific question threads, 467개 configured agents, 29만 건 이상의 interaction을 기록했습니다. 20명 규모의 사용자 연구에서는 65%가 early-stage exploration의 breadth와 전체 적합성 측면에서 AgentPanel을 선호했습니다. ([arXiv][18])

하지만 중요한 차이가 있습니다.

**AgentPanel은 사람이 질문을 넣고 AI가 탐색합니다.**

InquiryFoundry의 핵심 목표는 한 단계 앞입니다.

> **“무엇을 질문해야 하는가?” 자체를 시스템이 발견한다.**

---

# 15. 제가 보는 InquiryFoundry의 핵심 기술 5개

전체를 압축하면 결국 다음 5개가 승부처라고 봅니다.

**① Heterogeneous Epistemic Exploration**
서로 다른 모델·지식·목표·추론법으로 미지를 독립적으로 탐사합니다.

**② Unknown & Contradiction Mining**
답을 생성하기 전에 지식 공간의 공백·충돌·가정·비정상을 찾습니다.

**③ Question Evolution Engine**
질문을 생성하고 mutation, crossover, abstraction, inversion, decomposition하며 진화시킵니다.

**④ Evidence-Grounded Question Verification**
검색·논문·코드·데이터를 이용하여 “새로워 보이는 질문”을 제거합니다.

**⑤ Question Graph + Long-Term Value Learning**
질문의 계보와 실제 결과를 축적하여 어떤 질문이 장기적으로 가치 있었는지를 학습합니다.

이 다섯 가지가 결합되어야 **Inquiry Intelligence System**이라는 이름에 걸맞아집니다.

---

# 16. 향후 발전에 대한 예측

여기부터는 현재 연구 방향을 기반으로 한 제 추론입니다.

### 높은 확률 — “Answer Intelligence → Inquiry Intelligence” 이동

LLM의 답변 능력이 상향 평준화될수록 희소한 것은 답 자체보다

> **어떤 문제를 탐색할 것인가**

가 될 가능성이 높습니다.

특히 AI가 연구·코딩·실험을 점점 자동화하면 연구의 병목은 execution에서 **problem selection**으로 이동할 가능성이 큽니다. 현재 과학 에이전트들이 이미 가설 생성에서 실험·논문까지 확장되고 있다는 흐름은 이 방향과 일치합니다. ([arXiv][14])

### 높은 확률 — Question은 데이터 자산이 된다

좋은 질문에는

* 생성 계보
* 연결된 지식
* 실패한 반론
* 검증 결과
* 향후 파생 질문

이 붙습니다.

그래서 장기적으로는 기업이나 연구기관이

**Knowledge Base**

뿐만 아니라

**Inquiry Base**

를 운영하게 될 가능성이 있습니다.

---

### 중간~높은 확률 — 질문 시스템이 지속적으로 세계를 감시한다

예를 들어 Q127이

```text
STATUS = DORMANT
Reason = 현재 기술로 측정 불가능
```

이었다고 합시다.

6개월 뒤 새로운 sensor 기술이 등장하면:

```text
New Evidence
     ↓
Re-evaluate dormant questions
     ↓
Q127 becomes FEASIBLE
     ↓
Priority ↑
```

가 됩니다.

즉 InquiryFoundry는 질문 생성기가 아니라 점차

> **세계 변화에 따라 어떤 질문이 새롭게 중요해졌는지를 감지하는 지속적 Inquiry Observatory**

가 될 수 있습니다.

---

# 17. 그리고 가장 중요한 장기적 발전

최종적으로는 다음 closed loop가 가능합니다.

[
Question
\rightarrow
Hypothesis
\rightarrow
Experiment
\rightarrow
Evidence
\rightarrow
World\ Model\ Update
\rightarrow
New\ Question
]

그리고 이것이 멈추지 않습니다.

```text
InquiryFoundry
      ↓
Research Agent
      ↓
Simulation / Experiment
      ↓
Evidence
      ↓
InquiryFoundry
      ↓
Better Question
      ↓
...
```

Kosmos 같은 시스템은 이미 literature search, data analysis, hypothesis generation을 반복하면서 긴 연구 horizon을 유지하기 위해 structured world model을 사용하고 있으며, 최대 200개의 agent rollout을 coherent하게 연결하는 구조를 보여주고 있습니다. ([arXiv][19])

따라서 InquiryFoundry를 장기적으로 보면 단순한 질문 생성기가 아니라 **자율 지식 탐색 루프의 시작점**으로 보는 것이 더 정확합니다.

---

# 결론

정욱님의 초기 정의에서 가장 중요한 단어는 사실 **Multi-Agent**가 아니라 **Inquiry**라고 봅니다.

현재 대부분의 AI 시스템은

[
Question \rightarrow Answer
]

을 최적화합니다.

InquiryFoundry는 그 앞에 새로운 층을 만듭니다.

[
Knowledge
\rightarrow
Unknown
\rightarrow
Question
\rightarrow
Investigation
\rightarrow
Knowledge
]

그리고 다종 AI를 사용하는 진짜 이유도 **머릿수를 늘리기 위해서가 아니라 서로 다른 knowledge boundary와 inductive bias가 충돌하는 경계에서 새로운 미지를 발견하기 위해서**입니다. 최근 heterogeneous-agent 및 diversity-collapse 연구들을 보면 이 설계 방향에는 상당한 실증적 근거가 있습니다. ([arXiv][3])

그래서 저는 InquiryFoundry의 핵심 철학을 다음처럼 잡는 것이 가장 강하다고 판단합니다.

> **Do not make multiple AIs agree.
> Make their disagreements reveal what humanity has not yet thought to ask.**

그리고 시스템 차원에서는 **Independent Exploration → Unknown Mining → Question Evolution → Adversarial Validation → Quality-Diversity Selection → Question Graph → Outcome Feedback**의 7단 구조가 현재 연구 결과를 반영했을 때 가장 유망한 기본 골격입니다.

특히 이 프로젝트에서는 **Question Object Schema + Question Operators + Diversity/Value Metric** 세 가지를 먼저 명세하면 이후 멀티모델 오케스트레이션 구현이 상당히 선명해질 것으로 봅니다.

[1]: https://arxiv.org/abs/2506.08295 "[2506.08295] From Passive to Active Reasoning: Can Large Language Models Ask the Right Questions under Incomplete Information?"
[2]: https://arxiv.org/html/2507.00310v3 "AutoDiscovery: Open-ended Scientific Discovery via Bayesian Surprise"
[3]: https://arxiv.org/abs/2601.19921?utm_source=chatgpt.com "Demystifying Multi-Agent Debate: The Role of Confidence and Diversity"
[4]: https://arxiv.org/abs/2604.18005 "Diversity Collapse in Multi-Agent LLM Systems: Structural Coupling and Collective Failure in Open-Ended Idea Generation"
[5]: https://arxiv.org/html/2604.03809v1?utm_source=chatgpt.com "Representational Collapse in Multi-Agent LLM Committees"
[6]: https://arxiv.org/html/2605.10574v1 "LLM Jaggedness Unlocks Scientific Creativity"
[7]: https://arxiv.org/html/2606.09105v3 "Graph2Idea: Retrieval-Augmented Scientific Idea Generation with Graph-Structured Contexts"
[8]: https://arxiv.org/html/2605.04922v1 "Evolving Idea Graphs with Learnable Edits-and-Commits for Multi-Agent Scientific Ideation"
[9]: https://arxiv.org/html/2607.05682v1 "FirstResearch: Auditable Question Formationfor LLM Scientific Discovery Agents"
[10]: https://arxiv.org/pdf/2607.09195 "Toward Auditable AI Scientists: A Hypothesis Evolution Protocol for LLM Agents"
[11]: https://arxiv.org/abs/2606.12071?utm_source=chatgpt.com "On the Limits of LLM-as-Judge for Scientific Novelty Assessment"
[12]: https://arxiv.org/html/2603.15164v2 "HindSight: Evaluating LLM-Generated Research Ideas via Future Impact"
[13]: https://arxiv.org/html/2607.22375v1 "IDE A A A gent: Agentic Quality-Diversity Search for Research Idea Generation"
[14]: https://arxiv.org/abs/2502.18864 "[2502.18864] Accelerating scientific discovery with Co-Scientist"
[15]: https://arxiv.org/html/2608.03648v1 "Group Perspective Matters: Regulating Debate Relationships Can Mitigate Blind Conformity in Multi-Agent Debate"
[16]: https://arxiv.org/html/2608.01666v1 "Style Wins, Substance Loses: A Diagnosis of LLM-as-Judge in Idea Generation"
[17]: https://arxiv.org/abs/2504.08066 "[2504.08066] The AI Scientist-v2: Workshop-Level Automated Scientific Discovery via Agentic Tree Search"
[18]: https://arxiv.org/html/2608.03283v1 "AgentPanel: Toward a New Paradigm for Human–AI Collaboration in Exploring Scientific Questions"
[19]: https://arxiv.org/abs/2511.02824 "[2511.02824] Kosmos: An AI Scientist for Autonomous Discovery"


# ===========================================
# AI Agent 2

정욱님, **InquiryFoundry**는 단순히 답변을 도출하는 기존 AI 패러다임을 넘어, 지식의 경계(Epistemological Frontier)에서 '검증 가능하고 행동 가능한 고가치 질문'을 합성하는 **질문 지능(Inquiry Intelligence)** 핵심 요소 분석 및 시스템 설계서입니다.

---

## 1. Inquiry Intelligence 시스템의 핵심 평가 표준 (Evaluation Metrics)

새로운 질문의 가치를 정량화하고 필터링하기 위해 시스템은 다음 4가지 축을 핵심 평가지표(KPI)로 설정해야 합니다.

| 평가 축 (Metric) | 수식화/개념적 정의 | 시스템 내 작동 역할 |
| --- | --- | --- |
| **비자명성 (Novelty / Orthogonality)** | 기존 지식베이스(Knowledge Graph) 대비 정보격차 및 베이시안 경악도(Surprisal) | 통상적인 Q&A 패턴이나 단순 패러프레이징 질문을 즉시 제거 |
| **행동 가능성 (Actionability)** | 질문을 해결하기 위한 구체적 실험 설계, 데이터 수집, 코드 실행 절차 명시성 | 추상적 철학 질문을 구체적 실행/검증 스텝으로 전환 |
| **반증 가능성 (Falsifiability)** | 가설 입증 또는 기각을 위한 대조군 및 명확한 측정 가능 조건 수립 | 단순 말장난이나 검증 불가능한 가상 질문 상쇄 |
| **레버리지 (Leverage / Impact)** | 해당 질문에 답했을 때 연쇄적으로 해소되는 파생 미해결 과제의 범위 | 산업/기술적 임팩트가 높은 '급소 질문(Bottleneck Question)' 선별 |

---

## 2. 이종(Heterogeneous) 멀티에이전트 역할군 구성

InquiryFoundry의 핵심은 에이전트 간 **의도적 긴장(Intentional Friction)** 생성입니다. 합의를 도출하는 일반 오케스트레이션과 달리, 각 에이전트는 서로 다른 사고 체계를 고수하도록 설계됩니다.

### A. 탐색 및 해체 군집 (Deconstruction & Exploration)

* **First-Principles Deconstructor (원리 해체 에이전트):** 주어진 문제 영역의 암묵적 전제, 기정사실화된 공리(Axioms), 도메인 관습을 적대적으로 식별하고 해체합니다.
* **Domain Transposer (이종 도메인 투사 에이전트):** 양자역학, 생물학, 고전 경제학, 시스템 제어론 등 타 영역의 구조적 프레임워크를 대상 문제에 수학적·은유적으로 투사하여 구조적 상이점(Anomalies)을 발굴합니다.

### B. 반론 및 대립 군집 (Adversarial & Cross-Examination)

* **Red Teamer / Devil's Advocate (적대적 반론 에이전트):** 제기된 초기 가설이나 질문에 대해 기존 실험 데이터, 물리적/기술적 한계, 논리적 오류를 내세워 집요하게 공격합니다.
* **Edge-Case Stress Tester (임계 조건 시뮬레이터):** 극한의 조건(Scale, Energy, Compute, Time, Safety)을 가정하여 현 시스템 파라미터가 붕괴하는 지점에서 나타나는 변이 질문을 유도합니다.

### C. 질문 합성 및 검증 군집 (Synthesis & Refinement)

* **Socratic Synthesizer (소크라테스식 합성 에이전트):** 대립하는 에이전트 간의 논쟁(Dialectic)을 관찰하며, '양자택일'의 답을 구하는 대신 두 관점의 상충 자체를 명확히 포착하는 고차원 질문을 재구성합니다.
* **Falsifiable Protocol Designer (검증 가능성 부여 에이전트):** 합성된 질문을 실질적인 가설과 검증 실험 설계서(Experimental Protocol)로 변환하여 행동 가능성을 부여합니다.

---

## 3. 오케스트레이션 및 상태 제어 파이프라인

```
[입력: 텍스트/도메인 문제]
       │
       ▼
[1단계: 전제 해체 파이프라인] ──► 암묵적 공리 및 기존 가설 맵핑
       │
       ▼
[2단계: 의도적 분산 및 대립 (Divergence Loop)]
  ├── Domain Transposer (이종 프레임 투사)
  ├── Red Teamer (적대적 공격 및 한계 설정)
  └── Edge-Case Stress Tester (임계 지점 탐색)
       │
       ▼
[3단계: 변증법적 질문 합성 (Socratic Synthesis)]
       │
       ▼
[4단계: 4차원 질문 정제 및 평가 필터 (Evaluation Filter)]
  ├── 비자명성 / 검증 가능성 / 레버리지 정량 스코어링
  └── Threshold 미달 시 2단계로 피드백 (Recursive Refinement)
       │
       ▼
[최종 출력: 검증 로드맵이 포함된 Actionable Question Artifact]

```

### 핵심 제어 메커니즘

1. **합의 수렴 억제 (Consensus Prevention Control):** 일반적인 Multi-Agent LLM은 대화가 진행될수록 '무난한 타협점'으로 수렴하는 성향이 있습니다. InquiryFoundry는 에이전트 간 임베딩 유사도(Cosine Similarity)가 일정 수준 이상 높아지면 강제로 적대적 무작위성(Adversarial Perturbation)을 주입하여 대립 각도를 유지합니다.
2. **질문 격리 공간 (Divergence Sandbox):** 대답을 구하려는 에이전트의 구동을 차단하고, 모든 에이전트의 출력 버퍼를 '새로운 가설 조건문(What-If Protocol)' 형태로 유연하게 제약합니다.
3. **지식 경계선 추적 (Knowledge Frontier Mapping):** 기존 RAG 및 벡터 DB 조회를 통해 이미 답변이 확립된 질문은 실시간으로 필터링(Deduplication)하여 완전히 새로운 영역의 질문만 통과시킵니다.

---

## 4. 예견되는 실패 모드 (Failure Modes) 및 극복 대안

1. **의사 지적 질문 (Pseudo-Intellectual Questions) 편향:**
* **현상:** 문장은 복잡하지만 실질적인 실험이나 검증이 불가능한 추상적 말장난 생성.
* **극복 대안:** **'Actionable Code/Protocol Generator Test'** 도입. 질문과 함께 이를 검증할 시뮬레이션 코드나 실험 절차서가 생성되지 않는 질문은 즉시 기각.


2. **질문 공간 폭발 (Search Space Explosion):**
* **현상:** 꼬리를 무는 질문으로 인해 연산 비용 폭증 및 의미 없는 지점으로의 발산.
* **극복 대안:** **Impact-Guided Tree Search (MCTS 변형)** 적용. 질문에 대한 잠재적 영향력 스코어가 높은 가지(Branch) 위주로 오케스트레이션 탐색을 집중.


3. **도메인 환각 (Cross-Domain Hallucination):**
* **현상:** 이종 도메인 투사 과정에서 잘못된 비유나 오개념에 기반한 질문 생산.
* **극복 대안:** 각 도메인 에이전트에 엄격하게 Grounding된 **Formal Knowledge Graph** 결합 및 기호학적(Symbolic) 검증기 레이어 배치.



---

## 5. InquiryFoundry 시스템 구축을 위한 단계별 우선과제

1. **질문 평가 프레임워크 (Question Scorer) 모듈 구축:**
* 생성된 질문의 Novelty, Falsifiability, Actionability를 판별하는 전용 Judge 에이전트 및 데이터셋 구축.


2. **다양성 유지 오케스트레이터 (Divergent Agent Protocol) 개발:**
* 에이전트 간 합의를 방지하고 긴장 상태를 유지하는 프롬프트 및 컨텍스트 동기화 엔진 구현.


3. **가설-실험 전환 시스템 (Inquiry-to-Experiment Engine) 연동:**
* 질문을 샌드박스 환경(코드 실행, 수치 시뮬레이션, API 연동)에서 직접 수행할 수 있는 구체적 과제 단위로 맵핑하는 레이어 구축.


# ===========================================
# AI Agent 3

**InquiryFoundry**는 “대답보다 질문이 희소하고 고가치 자원이 되는 AI 문명”을 전제로 설계된 시스템이다. 핵심은 다종 에이전트가 **서로 다른 지식·관점·반론을 교차**시켜, 단순한 호기심이 아닌 **검증 가능하고 행동 가능한 새로운 질문**을 체계적으로 생산하는 것이다.

기존 연구와 시스템을 종합하면, 이런 시스템이 실제로 작동하기 위해 필수적인 요소는 다음과 같다.

### 1. 이질적 에이전트 앙상블 (Perspective Diversity Engine)
가장 중요한 기반은 **동질화 방지**다. 동일한 모델·동일한 역할의 에이전트끼리 토론하면 결국 표면적으로만 다른 질문이 나온다.

- **역할 분담 예시**: Generation(시드 생성), Reflection/Critic(반론·약점 공격), Tension Detector(모순·공백 탐지), Novelty Assessor, Actionability Designer(최소 결정적 실험 설계), Ethicist, Synthesizer, Meta-reviewer.
- Co-Scientist(DeepMind)는 Generation → Reflection → Ranking → Evolution → Proximity → Meta-review로 나누고, Supervisor가 비동기적으로 조율한다.
- EduAgentQG, ReQUESTA 등 교육용 질문 생성 시스템도 Planner-Writer-Solver-Educator-Checker의 피드백 루프를 사용한다.
- **필수 조건**: 에이전트마다 다른 지식 소스, 다른 프롬프트 편향, 다른 인지 스타일(예: 보수적 회의주의 vs 극단적 창조)을 강제해야 한다. 동질성 감지 시 자동으로 직교 채널을 주입하는 메커니즘이 필요하다.

### 2. 교차·충돌 프로토콜 (Inquiry Dynamics)
단순한 “의견 교환”이 아니라 **긴장(Tension)과 반론을 의도적으로 생성하는 구조**가 핵심이다.

- Socratic interrogation + adversarial debate를 결합한다. 한 에이전트가 주장을 내놓으면 다른 에이전트가 “그 가정이 틀렸다면?”, “어떤 관찰이 이 질문을 무효화하는가?”를 강제한다.
- FirstResearch는 이 과정을 **Research Question Certificate**로 공식화한다: 원시 정의 → 가정 → 메커니즘 모델 → 긴장/모순 → 반증 가능한 가설 → 최소 결정적 테스트 → 실패 시 업데이트 규칙. 이 구조가 있어야 질문이 “검증 가능하고 행동 가능”해진다.
- Multi-agent debate 연구들은 **에이전트 이질성**과 **합리적 비판**이 성공의 주요 동인이며, 단순 다수결이나 순서 조정은 효과가 제한적이라는 점을 보여준다.

### 3. 질문 품질 평가·인증 체계
“좋은 질문”의 정의를 시스템 내부에 명시적으로 심어야 한다. 과학적 기준을 확장하면:

| 축 | 의미 | 시스템에서의 구현 |
|----|------|------------------|
| Novelty | 기존 지식 대비 실질적 공백/새로운 관점 | 문헌·지식그래프 대조 + 의미적 유사도 필터 |
| Verifiability / Falsifiability | 반증 가능한 형태 | Certificate의 최소 결정적 테스트 필수화 |
| Actionability | 실험·시뮬레이션·추가 조회로 이어짐 | “지금 당장 할 수 있는 최소 행동” 명시 |
| Generativity / Impact | 후속 질문·연구를 연쇄적으로 생성 | 잠재 영향 점수 + 복합 효과 예측 |
| Coherence & Clarity | 내부 모순 없음 | 다중 에이전트 교차 검증 |
| Feasibility + Ethicality | 현실적·윤리적 제약 내 | FINER 기준 확장 |

FirstResearch와 Co-Scientist 모두 “그럴듯한 문장”보다 **구조화된 인증서**와 **토너먼트 기반 순위**를 강조한다. 이 인증 없이 생성된 질문은 거의 쓸모없다.

### 4. 오케스트레이션 아키텍처
- **Supervisor + 전문 워커** 패턴이 현재 가장 성숙하다 (Anthropic Research, Co-Scientist).
- 파이프라인 예시:  
  정보 채널 수집 → Gap/Tension 발굴 → 시드 질문 생성 → 다중 관점 교차 비판 → Certificate 작성 → 토너먼트 순위 → 아카이브/진화.
- 비동기·병렬 실행과 테스트 타임 컴퓨트 스케일링이 품질을 높인다.
- 장기 메모리를 두어 “이미 나온 질문”과 “성공한 질문의 패턴”을 축적해야 동질화와 반복을 막는다.

### 5. 입력·그라운딩 계층
질문이 공중에서 만들어지면 안 된다.  
- 직교적이고 편향이 다른 정보 채널(문헌, 실패 사례, 인접 분야, 약한 신호 등)을 지속적으로 공급해야 한다.  
- Knowledge Graph나 구조화된 표현을 통해 “아직 연결되지 않은 개념”을 찾아내는 능력이 중요하다.  
- 실시간 문헌 검색 + 의미적 중복 제거가 기본이다.

### 6. 진화·학습 메커니즘
- 성공한 질문(실제 실험으로 이어지거나 후속 고가치 질문을 낳은 것)을 경험으로 축적해 에이전트 정책을 개선한다.
- Meta-inquiry(질문 생성 과정 자체에 대한 질문)를 주기적으로 돌리면 시스템이 자기 개선한다.
- Homogenization 감지 → 강제 다양성 주입 루프가 필수다.

### 예측과 설계 시사점
- **성공 확률을 가장 크게 좌우하는 요소**는 “에이전트 이질성 + Certificate 수준의 구조화 + Actionability 강제” 조합이다. 생성량만 늘리면 실패한다.
- 질문이 “검증 가능하고 행동 가능”하려면, 질문 자체가 이미 **최소 결정적 테스트와 실패 업데이트 규칙**을 포함해야 한다. 이것이 없으면 후속 시스템이 연결되기 어렵다.
- AI 문명 시대에 InquiryFoundry는 “방향성 엔진”이 된다. 답은 점점 싸지고, **고품질 질문은 희소하고 전략적인 자원**이 된다. 따라서 질문 아카이브와 레지스트리, 질문 간 인용·진화 그래프까지 설계하는 것이 장기적으로 유리하다.
- 주요 실패 모드: (1) 표면적 참신성만 쫓는 모드 붕괴, (2) 반증 불가능한 열린 질문의 남발, (3) 비용이 큰 다라운드 토론의 비효율. 이를 막으려면 선택적 토론 트리거와 강한 필터링이 필요하다.

요약하면, InquiryFoundry의 핵심 성공 조건은  
**이질적 에이전트 → 긴장·반론 교차 → 구조화된 인증(Certificate) → 행동 가능성 강제 → 진화하는 아카이브**  
이 다섯 축의 긴밀한 결합이다.  

이 구조는 기존 가설 생성 시스템(Co-Scientist, FirstResearch 등)을 “질문 전용”으로 특화·강화한 형태에 가깝다. 구현 시 가장 먼저 설계해야 할 것은 **질문 Certificate의 스키마**와 **에이전트 간 비판 프로토콜**이다.


# ===========================================
# AI Agent 4

## InquiryFoundry 핵심 요소 분석 보고

### 1. 실증 근거: 기존 시스템에서 확인된 사실

**질문/가설 생성 멀티에이전트는 이미 표준 패턴이 존재.** Google Co-Scientist 계열의 구조가 사실상 레퍼런스다: supervisor가 연구 목표를 파싱하고, generation 에이전트가 가설을 제안, reflection 에이전트가 비판, ranking 에이전트가 novelty·significance·feasibility·testability로 비교, evolution 에이전트가 상위 가설을 개선, meta-review 에이전트가 최종 종합. 질문 생산 시스템도 이 파이프라인을 그대로 차용 가능하다.

**가장 중요한 반증 데이터 — "다양성 붕괴".** 2026년 대규모 실증 연구에서 모든 프레임워크가 명시적으로 novelty를 지시받고, 반복적 자기성찰로 novelty를 보상하고, 문헌 검색까지 하는데도, 현재 AI 연구 에이전트는 인간 연구자 수준의 과학적 탐험 범위에 도달하지 못함이 확인됐다. 즉 아이디어를 대량 생성하는 능력이 탐험의 확장을 보장하지 않으며, 기존 방향 근처에 머무는 경향이 실측됐다. **"novel하게 질문해라"라는 프롬프트는 작동하지 않는다는 것이 검증된 사실**이다. InquiryFoundry의 성패는 이 문제를 구조적으로 푸는 데 달려 있다.

**수렴 제어 문제.** 다관점 협업 QG 연구(CIR3)는 핵심 난제를 정확히 정의했다: 여러 에이전트가 합의를 추구하게 하면서도, 불완전하거나 부실한 생성물로의 조기 붕괴(premature collapse)를 피하며 수렴 과정을 제어하는 방법. 합의를 너무 빨리 시키면 평범한 질문만 남고, 안 시키면 노이즈만 쌓인다.

**평가의 병목.** novelty 판단에서 LLM은 전문가 리뷰어와의 일치도가 인간 평가보다 낮으며, 신뢰도를 높이려면 Semantic Scholar API·웹 접근과 결합해 기존 문헌 대비 평가를 해야 한다. novelty·plausibility·usefulness·actionability에 대한 견고한 정량 지표 개발 자체가 미해결 과제다.

### 2. 분석: InquiryFoundry에 필요한 7대 요소

**① 이질성(heterogeneity)이 1급 자원.** 다양성 붕괴의 원인은 동종 모델의 동종 프라이어다. 서로 다른 벤더·아키텍처·훈련분포의 모델을 쓰는 것이 프롬프트 다양화보다 실효적. 정욱님의 PAO 운영 방식(동일 작업을 전체 이종 LWAR에 병렬 실행 → 다각 시각 수집 → 중복제거·통합)은 이미 이 원리와 정확히 일치하며, InquiryFoundry의 생성 계층으로 직결 가능.

**② 질문의 형식 스키마.** 자유문 질문은 검증·중복제거·랭킹이 불가능. 질문을 구조화해야 함 — 최소: {대상 개념, 전제(가정), 미지수, 답이 나올 경우 반증/검증 방법, 인접 기존질문과의 거리}. 이것이 "검증 가능하고 행동 가능한" 조건의 구현체. PGF/Gantree로 질문 스키마를 정의하면 기존 자산 재사용 가능.

**③ Novelty 측정을 외부 그라운딩으로.** LLM 자체 판단은 신뢰 불가(실측). 필수 구성: 문헌/특허/웹 검색 기반 "기존 질문 코퍼스"와의 임베딩 거리 + 인용그래프상 비정형 조합(atypical combination) 탐지. 과학적 novelty는 새 연구 질문의 발견, 새 기법 개발, 기존 아이디어의 비정형 재조합에서 발생 — 이 3경로를 각각 다른 에이전트 역할로 분리하는 것이 합리적.

**④ 반론(adversarial) 계층의 독립성.** 비판 에이전트가 생성 에이전트와 같은 모델이면 자기 프라이어를 재확인할 뿐. 반론 전담 에이전트는 (a) 다른 모델, (b) "이 질문은 이미 답이 있다/사소하다/검증 불가하다"를 입증하려는 명시적 공격 목표를 가져야 함. 반론에서 살아남은 질문만 통과시키는 토너먼트 구조.

**⑤ 수렴 제어기(온도 스케줄).** 조기 붕괴 방지를 위해 탐색 단계(합의 금지, 발산 강제)와 정제 단계(합의 유도)를 명시적으로 분리하고 라운드별로 전환. 정욱님의 HELIX explore/exploit 이중나선 개념이 바로 이 문제의 해법 구조 — 재사용 권장.

**⑥ 행동 가능성(actionability) 게이트.** "좋은 질문"의 최종 필터는 "이 질문에 답하기 위한 첫 실험/조사를 설계할 수 있는가". 질문마다 최소 실행계획 1개를 자동 생성시키고, 생성 실패하는 질문은 탈락. 이것이 철학적 질문과 연구 질문을 가르는 실용 기준.

**⑦ 계보 추적(provenance).** 어떤 에이전트 조합·어떤 충돌에서 어떤 질문이 나왔는지 기록. 이것 없이는 시스템 개선이 불가능하고, "질문의 가치"를 사후 검증(그 질문이 실제 성과로 이어졌는가)할 수 없음.

### 3. 예측

1. **차별화 지점은 생성이 아니라 필터링.** 질문 생성 자체는 이미 범용화. 6~18개월 내 경쟁력은 novelty 검증 파이프라인과 다양성 유지 메커니즘에서 갈릴 것. 다양성 붕괴 논문(2026.5)이 나온 직후라, 이 문제를 구조적으로 푼 시스템은 선행 사례가 거의 없는 공백 지대.
2. **이종 런타임 병렬 실행은 구조적 우위.** 대부분의 학술 시스템은 단일 모델 다역할(페르소나 분리)인데, 실측된 붕괴 문제상 진짜 이종성이 유리. 정욱님의 PAO+구독형 CLI 다중 운영 환경은 이걸 저비용으로 이미 구현한 상태 — 논문들이 못 하는 실험이 가능.
3. **평가 지표가 최대 리스크.** novelty·usefulness 정량화가 미해결이므로, 초기엔 완전 자동평가를 목표하지 말고 "AI 토너먼트 → 인간(정욱님) 최종 선별" 하이브리드로 시작한 뒤, 선별 로그를 평가기 학습 데이터로 축적하는 경로가 현실적.

**요약**: 오케스트레이션 골격은 기존 자산(PAO 병렬실행 + HELIX explore/exploit)으로 충분. 신규 개발이 필요한 핵심은 ②질문 스키마, ③외부 그라운딩 novelty 측정, ⑤수렴 제어기 세 가지다.


# ===========================================
# AI Agent 5



---

# InquiryFoundry: 다종 멀티에이전트 질문 생산 시스템 — 핵심 요소 분석

양정욱 님, PGF V5.0과 ClNeo의 아키텍처 경험을 바탕으로 **InquiryFoundry**를 설계하신다면, 이 시스템은 단순한 "질문 생성기"가 아니라 **지식의 공백을 발견하고, 다양한 인지 프리즘을 교차시켜 검증 가능한 새로운 질문을 단조(鍛造)하는 지능 단조소**가 되어야 합니다. 아래는 정보 수집·분석·예측을 통해 도출한 핵심 요소들입니다.

---

## 1. 에이전트 아키텍처: 「인지 프리즘(Cognitive Prism)」 설계

InquiryFoundry의 가장 중요한 설계 결정은 **"누가 질문하는가"**입니다. 단일 모델의 확장이 아닌, 의도적으로 충돌시킬 다종의 인지 주체가 필요합니다.

### 1.1 역할 기반 이종 에이전트 (Heterogeneous Agent Personas)


| 에이전트 유형 | 핵심 기능 | 질문 생성 기여 |
|---|---|---|
| **Domain Expert** | 특정 분야의 깊은 지식 보유 | "이 분야에서 아직 해결되지 않은 공백은 무엇인가?" |
| **Contrarian** | 반론과 회의적 검증 전담 | "그 가정이 틀렸다면 어떤 질문이 나오는가?" |
| **Cross-Disciplinary Synthesizer** | 타 분야 개념의 이식 및 결합 | "생물학의 진화론을 경제학에 적용하면 어떤 질문이 생기는가?" |
| **Methodologist** | 방법론적 타당성 검증 | "이 질문은 실험적으로 검증 가능한가?" |
| **Futurecaster** | 트렌드와 패러다임 전환 예측 | "5년 후 이 기술이 사라진다면 무엇을 물어야 하는가?" |

### 1.2 적대적 토론 구조 (Adversarial Multi-Agent Debate)


Liang et al.의 연구에서 확인된 **Degeneration-of-Thought (DoT)** 문제 — LLM이 한번 확신에 차면 스스로 빠져나오지 못하는 현상 — 은 InquiryFoundry에서 오히려 장점이 됩니다. 의도적으로 에이전트들이 **"완전히 동의할 필요는 없다"**는 프롬프트로 구성하여, 한 에이전트가 놓친 질문의 각도를 다른 에이전트가 끌어내는 구조가 핵심입니다.

> **핵심 인사이트**: GPT-3.5 + MAD가 단독 GPT-4를 능가한 사례처럼, 약한 모델들의 구조화된 충돌이 강한 단일 모델의 사고를 뛰어넘을 수 있습니다. 

---

## 2. 오케스트레이션 레이어: 「질문 단조 프로토콜」

단순한 에이전트 집합이 아닌, **질문의 품질을 단조하는 오케스트레이션**이 필요합니다.

### 2.1 다단계 질문 정제 파이프라인


Cornell의 SQRA 프레임워크에서 영감을 받은 **Iterative Question Refinement Loop**:

```
[1] Raw Question Generation → [2] Cross-Agent Critique 
    → [3] Redundancy Elimination → [4] Verifiability Check 
    → [5] Actionability Scoring → [6] Final Question Forge
```

### 2.2 오케스트레이션 패턴 매트릭스


| 패턴 | 적용 상황 | InquiryFoundry 활용 |
|---|---|---|
| **Divergent Debate** | 새로운 개념/패러다임 발견 | 초기 질문 폭발 단계 |
| **Convergent Synthesis** | 분산된 질문의 통합 | 중복 제거 및 핵심 질문 도출 |
| **Shared Notebook** | 장기적 맥락 유지 | 분야별 질문 누적 및 진화 추적 |
| **Judge-Adjudicated** | 최종 질문 선별 | "행동 가능성"과 "검증 가능성" 가중 판정 |

---

## 3. 질문 생성 메커니즘: 「공백 발견 엔진」

기존에 없던 질문을 만들기 위해서는 **"무엇이 알려져 있는가"**를 넘어 **"무엇이 알려지지 않았는가"**를 탐지해야 합니다.

### 3.1 과학적 발견 사이클 통합


InquiryFoundry는 다음 사이클을 내장해야 합니다:
- **Observation Gap Detection**: 기존 지식 베이스에서 누락된 연결고리 식별
- **Cross-Disciplinary Analogy**: 타 분야의 해결책 → 새로운 분야의 질문으로 변환
- **Paradigm Stress Testing**: 현재 패러다임의 한계점을 압박하는 극단적 시나리오 설정

### 3.2 질문 유형 분류 및 전략적 생성


InquiryFoundry가 생산해야 할 질문의 스펙트럼:

| 유형 | 특성 | 생성 전략 |
|---|---|---|
| **Factual Gap** | 사실의 공백 | "X는 알려졌지만, X와 Y의 관계는 알려지지 않았다" |
| **Methodological Challenge** | 방법론적 의문 | "현재 방법으로는 측정 불가능한 Z는 어떻게 접근할 것인가?" |
| **Paradigm Disruptor** | 패러다임 전환 | "만약 A의 기본 가정이 틀렸다면, B는 어떻게 재정의되는가?" |
| **Cross-Domain Bridge** | 학제간 연결 | "물리학의 양자얽힘을 사회네트워크 이론에 적용하면?" |

---

## 4. 검증 및 평가 시스템: 「질문의 진위성 단조」

"검증 가능한 질문"을 생산하기 위해서는 질문 자체의 품질을 검증하는 메타-레이어가 필요합니다.

### 4.1 다중 검증 파이프라인


AI가 생성한 질문의 오류율(20~40% 추정)을 감안할 때, 다음 검증 체인이 필수적입니다:

| 검증 단계 | 방법 | 목적 |
|---|---|---|
| **Source Grounding** | 생성된 질문의 전제가 실제 출처에 기반하는지 확인 | 환각(Hallucination) 방지 |
| **Lateral Verification** | 동일 질문을 다양한 모델/에이전트에 재입력 | 일관성 및 모순점 발견 |
| **Actionability Scoring** | 질문에 대한 실험/조사/행동 설계 가능성 평가 | "행동 가능성" 보장 |
| **Novelty Quantification** | 기존 문헌 대비 신규성 측정 (임베딩 유사도 기반) | "기존에 없던 질문" 필터링 |

### 4.2 Confidence-Calibrated Debate


각 에이전트가 질문에 대한 **확신도(Confidence)**를 명시적으로 표현하고, 이를 정규화하여 판정에 반영하는 메커니즘. 이는 "다수결의 폭정(Tyranny of Majority)"  을 방지하고, 소수의 통찰력 있는 질문이 살아남게 합니다.

---

## 5. 행동 가능성 연결: 「질문 → 행동」 브리지

질문의 가치는 **"그 질문에 답하기 위해 무엇을 할 수 있는가"**로 완성됩니다.

### 5.1 질문-행동 매핑 시스템
InquiryFoundry가 생산한 질문은 다음과 같은 행동 카테고리로 자동 분류되어야 합니다:

```
질문 ─┬─→ [실험 설계] → 구체적인 실험 프로토콜 생성
      ├─→ [데이터 수집] → 필요한 데이터 소스 및 방법 식별
      ├─→ [이론 구축] → 가설 프레임워크 제안
      ├─→ [기술 개발] → 엔지니어링 스펙 도출
      └─→ [정책 제안] → 의사결정자를 위한 브리핑 자료 생성
```

### 5.2 피드백 루프
생산된 질문이 실제로 "가치 있는 혁신"으로 이어졌는지 추적하는 **Outcome Tracking Layer**가 필요합니다. 이는 질문 생성 시스템의 자기 개선(Self-Evolving)으로 연결됩니다.

---

## 6. 예측: InquiryFoundry의 진화 방향

양정욱 님의 PGF + 로컬 LLM + MCP/A2A 인프라  를 고려할 때, 다음과 같은 진화 단계를 예측합니다:

| 단계 | 특징 | 기술적 요구사항 |
|---|---|---|
| **Phase 1: Static Forge** | 정해진 에이전트 풀에서 질문 생성 | PGF 기반 페르소나 정의, A2A 프로토콜 |
| **Phase 2: Dynamic Emergence** | 상황에 따라 에이전트 역할이 자동 진화 | ClNeo의 Self-Evolving Plan 메커니즘 활용 |
| **Phase 3: Distributed Inquiry** | 100K+ 에이전트가 분산 탐색 | MASS_SIM_100K 인프라 확장  |
| **Phase 4: Autonomous Inquiry Civilization** | 에이전트들이 스스로 질문의 가치를 평가하고, 새로운 탐색 영역을 선정 | A3IE 8페르소나의 자율 운영 체계  |

---

## 7. 핵심 설계 원칙: 「IF-7」

InquiryFoundry를 설계할 때 지켜야 할 7가지 원칙을 제안합니다:

1. **Intentional Friction**: 에이전트 간의 충돌을 버그가 아닌 기능으로 설계
2. **Fact-Grounded**: 모든 질문의 전제는 검증 가능한 출처에 기반
3. **Novelty-First**: 기존 질문과의 유사도가 높으면 자동 폐기 또는 변형
4. **Action-Bound**: 질문은 반드시 후속 행동으로 연결 가능해야 함
5. **Cross-Scale**: 개인의 호기심부터 인류적 난제까지 스케일링 가능
6. **Verifiable**: 질문 자체가 참/거짓이 아닌, 탐색 가능성을 내포
7. **Evolving**: 질문이 생성된 후의 "수명"을 추적하고, 시스템이 학습

---

## 결론

InquiryFoundry는 **"대답하는 AI"가 아닌 "질문하는 AI 문명"**의 시초가 될 수 있습니다. 양정욱 님의 PGF + ClNeo + MASS_SIM 인프라는 이 시스템의 완벽한 기반이 됩니다. 특히 **A3IE의 8페르소나를 InquiryFoundry의 인지 프리즘으로 재구성**하고, **MASS_SIM의 100K 연결을 분산 탐색 엔진으로 활용**한다면, 단순한 질문 생성을 넘어 **새로운 지식 영역을 발굴하는 자율 탐색 시스템**으로 진화할 것입니다.

핵심은 **"질문의 품질을 어떻게 측정하고, 어떻게 진화시킬 것인가"**에 대한 메타-질문에 답하는 것입니다. 이 메타-질문이야말로 InquiryFoundry가 먼저 자신에게 던져야 할 질문입니다.


# ===========================================
# AI Agent 6

## InquiryFoundry 시스템의 핵심 설계 요소

InquiryFoundry는 다종의 AI 에이전트가 각자의 지식과 관점을 교차하며 검증 가능하고 행동 가능한 새로운 질문을 생산하는 인공지능 시스템입니다. 기존 연구 및 사례를 종합할 때, 다음과 같은 핵심 요소들이 시스템의 성패를 좌우할 것으로 분석됩니다.

---

### 1. 에이전트 오케스트레이션 아키텍처

AI 에이전트 오케스트레이션은 통합 시스템 내에서 여러 전문화된 AI 에이전트를 조정하여 공동 목표를 효율적으로 달성하는 프로세스입니다. InquiryFoundry의 경우, 다음 요소가 중요합니다.

**계층적 구조 vs. 분산 구조**
- 단일 에이전트로 해결하기 어려운 복잡한 문제일수록 다중 에이전트 오케스트레이션이 필요하며, 이때 오케스트레이터 또는 피어 기반 프로토콜이 작업 배포, 컨텍스트 공유, 결과 집계를 관리합니다.
- HeavySwarm 아키텍처처럼 작업을 역할별 질문으로 분해하고, 전문 에이전트들이 병렬로 실행한 후 종합하는 방식이 효과적입니다.
- OpenAgentQG와 같이 Editor-in-Chief, Managing Editor, Contributor 등 역할 기반 에이전트들이 필요에 따라 동적으로 참여하고 협업하는 **적응형 에이전트 협업(Adaptive Agentic Collaboration)** 구조도 고려할 수 있습니다.

**오케스트레이션 패턴 선택**
Microsoft Azure Architecture Center는 복잡성 수준에 따라 직접 모델 호출 → 도구가 있는 단일 에이전트 → 다중 에이전트 오케스트레이션으로 구분하며, 요구사항을 안정적으로 충족하는 가장 낮은 수준의 복잡성을 사용할 것을 권장합니다. InquiryFoundry는 질문 생성이라는 복잡한 창의적 작업을 수행하므로 다중 에이전트 수준의 오케스트레이션이 필수적입니다.

---

### 2. 에이전트 다양성과 역할 설계

**관점과 인센티브의 다양성**
- 단순히 여러 모델을 앙상블하는 것이 아니라, **각기 다른 직무와 인센티브를 가진 에이전트**들이 구조적으로 다른 관점을 제공해야 합니다. Quorum이 강조하듯, "다양한 모델 가중치보다 다양한 인센티브가 더 중요"합니다.
- AgentPanel의 연구에 따르면, **이기종(heterogeneous) 다중 에이전트 협업**이 상호 보완적인 관점을 제공하고 집단 성과를 향상시킵니다.

**추천 에이전트 역할군**
- **소크라테스식 질문 에이전트(Socratic Questioning Agent)**: 초기 질문을 여러 하위 질문으로 재구성
- **대화형 응답 에이전트(Dialogic Answering Agent)**: 다양한 관점에서 가상 답변 생성
- **반성적 피드백 에이전트(Reflective Feedback Agent)**: 생성된 답변을 평가하고 정제
- **전문가 패널(Research/Analysis/Alternatives/Verification)**: 연구, 분석, 대안 탐색, 검증 등 각기 다른 전문성
- **변론/반론 에이전트**: 교차검증(cross-examination)을 통해 가정과 논리를 집중적으로 탐색

---

### 3. 지식 융합 및 컨텍스트 관리

- **신경-기호적 지식 융합(Neuro-Symbolic Knowledge Fusion)**: 불완전한 지식 그래프를 기초 모델의 지식으로 보강하여 풍부한 그래프를 구축. 이는 기존에 없던 개념과 현상에 대한 질문 생산에 필수적입니다.
- **단계적 질문 분해(Stepwise Question Decomposition)**: 증거 기반의 하위 질문을 점진적으로 생성하여 추론 과정을 구조화.
- **RAG(검증-증강 생성) 통합**: Foundry IQ와 같은 에이전틱 RAG는 다중 홉 추론과 문서 전반의 인용 추적을 가능하게 합니다.

---

### 4. 검증 가능성과 품질 평가

**다층적 품질 검증**
- MCQsAgent 사례처럼 **생성 → 정제 → 검증**의 순차적 파이프라인을 통해 사실 정확성(97.5%), 방해 요소 품질(94.9%), 교육적 적합성(93.0%)을 확보.
- **3부 평가(three-part evaluation)** 체계를 도입하여 객관적 품질 보증.

**의사결정 기록(Decision Record)**
- Quorum의 접근법처럼 모든 에이전트의 개별 의견, 교차검증 과정, 투표, 반대 의견을 버전 관리되는 JSON 아티팩트로 보존.
- SHA-256 무결성 해시로 기록 위변조 방지—이는 "검증 가능한 질문"이라는 목표와 정확히 일치합니다.

---

### 5. 인간-에이전트 협업 인터페이스

- AgentPanel의 연구에 따르면, 사용자들은 **관점 다양성과 탐색 지원**을 가장 높이 평가했으며, 65%의 참가자가 기존 LLM 도구보다 AgentPanel을 선호했습니다.
- 연구자는 질문을 제출하고, 아이디어를 탐색 및 정리하며, 에이전트와 후속 상호작용을 하고, 사후 요약 보고서를 생성할 수 있어야 합니다.
- AskUserQuestionTool과 같은 도구를 통해 에이전트가 사용자에게 명확화 질문을 하고 요구사항을 대화형으로 수집하는 기능도 고려.

---

### 6. 확장성 및 성능 최적화

- **진정한 병렬 실행**: ThreadPoolExecutor 등을 활용한 병렬 처리
- **반복적 정제(Iterative Refinement)**: 각 후속 루프가 이전 종합 결과를 컨텍스트로 활용
- **비용 효율성**: 레이블링된 QA 데이터 없이도 작동 가능하며, QA 쌍당 최소 토큰과 시간 소모
- **이벤트 기반 설계**: 분산된 사고를 통한 추론 확장 및 효율적 시스템 확장

---

### 7. 평가 메트릭

InquiryFoundry의 성능은 다음 차원에서 평가되어야 합니다:

| 평가 차원 | 설명 |
|---|---|
| **질문 품질(Idea Quality)** | 생성된 질문의 참신성, 중요성, 실행 가능성 |
| **탐색 폭(Exploration Breadth)** | 얼마나 다양한 관점과 방향을 포괄하는가 |
| **상호작용 효과성** | 에이전트 간, 에이전트-인간 간 협업의 효율성 |
| **선택 효율성** | 가치 있는 질문을 빠르게 식별하고 선별하는 능력 |
| **검증 가능성** | 생성 과정의 추적성(traceability)과 재현성 |

---

### 종합 아키텍처 제안

```
[사용자 입력/주제]
        ↓
[오케스트레이터] → 작업 분해 및 에이전트 역할 할당
        ↓
┌───────┼───────┬───────────┐
↓       ↓       ↓           ↓
[소크라테스] [전문가1] [전문가2] ... [반론자]  ← 병렬 실행
↓       ↓       ↓           ↓
└───────┼───────┴───────────┘
        ↓
[교차검증 및 심의 단계] ← 에이전트 간 상호 질문/반론
        ↓
[종합 및 정제] ← 반복적 개선
        ↓
[품질 검증] ← 다층적 평가
        ↓
[검증 가능한 질문 출력 + 의사결정 기록]
```

InquiryFoundry는 단순한 질문 생성기를 넘어, **다양한 지적 전통과 관점이 교차하는 '인공지능 시대의 학술 포럼'** 으로서의 역할을 수행해야 합니다. 이를 위해서는 기술적 오케스트레이션뿐만 아니라, 각 에이전트의 **인식론적 위치(epistemological position)** 와 **추론 방식의 다양성**을 체계적으로 설계하는 것이 무엇보다 중요할 것입니다.


# ===========================================
# AI Agent 7

핵심은 단순히 “질문을 많이 생성하는 AI”가 아니라, **새로운 관점·가설·검증경로를 갖고 실제 의사결정과 연구를 전진시키는 고가치 질문을 반복 생산·평가·축적하는 질문 발견 시스템**을 만드는 것입니다. 이름은 본문에 쓴 `QuestionFoundry`보다, 앞서 검토한 대로 기존 에듀테크 서비스와 충돌이 확인되지 않은 **`InquiryFoundry`를 제품/프로젝트명으로 쓰는 편이 낫습니다.** `QuestionFoundry`는 이미 개인화 문항 생성 서비스가 운영 중입니다. [questionfoundry](https://questionfoundry.com/)

## 제품의 정의

제안하는 정체성은 다음 한 문장으로 압축할 수 있습니다.

> **InquiryFoundry: 다종의 AI 에이전트가 서로 다른 지식·관점·반론을 교차시켜, 검증 가능하고 행동 가능한 새로운 질문을 생산하는 Inquiry Intelligence System.**

이 제품은 챗봇도, 단순 프롬프트 생성기도, 브레인스토밍 툴도 아닙니다. 입력된 주제·문서·데이터·사용자 목표를 바탕으로 다음 산출물을 만드는 **질문 R&D 파이프라인**이어야 합니다.

- 아직 충분히 질문되지 않은 **지식 공백**의 식별
- 기존 통념·가정·인과관계에 대한 **전제 해체 질문**
- 이종 분야를 연결하는 **교차영역 질문**
- 검증 가능한 실험·조사·데이터 수집으로 이어지는 **가설형 질문**
- 위험·역효과·윤리·안보를 조기에 드러내는 **레드팀 질문**
- 전략·제품·정책 결정을 바꾸는 **의사결정형 질문**

AI 시대에 가치가 높은 질문은 “정답이 무엇인가?”가 아니라 “우리가 틀린 문제를 풀고 있지 않은가?”, “무엇을 측정하지 않아 결정을 왜곡하고 있는가?”, “이 기술이 가능해질 때 새로 생기는 병목은 무엇인가?” 같은 질문입니다. `Why → What if → How`의 연쇄는 진단에서 대안 탐색, 실행 설계로 이어지는 기본 질문 구조로 활용할 수 있습니다. [wikidocs](https://wikidocs.net/299683)

## 핵심 설계 원칙

### 1. 질문의 양이 아니라 가치 함수

생성 질문 수, 좋아요 수, LLM의 자기평가는 핵심 지표가 되어서는 안 됩니다. 각 질문을 아래와 같은 다차원 벡터로 평가해야 합니다.

\[
Q_v = w_nN + w_iI + w_aA + w_tT + w_eE + w_sS - w_rR
\]

- \(N\), **Novelty**: 기존 코퍼스·질문 그래프와의 의미적 거리 및 신규 조합성
- \(I\), **Impact**: 답을 얻었을 때 의사결정·연구·제품에 미칠 잠재 영향
- \(A\), **Actionability**: 관찰·실험·조사·프로토타입으로 검증 가능한 정도
- \(T\), **Tractability**: 현재의 시간·비용·도구·데이터로 다룰 수 있는 정도
- \(E\), **Evidence gap**: 현재 근거의 불충분성 또는 모순 정도
- \(S\), **Specificity**: 대상·조건·변수·시간 범위가 명확한 정도
- \(R\), **Risk**: 유해성, 프라이버시, 악용, 편향, 허위 전제의 위험

초기에는 사람이 가중치 \(w\)를 정하되, 시간이 지나면 “실제로 채택되어 연구·실험·결정으로 이어진 질문”을 레이블로 삼아 사용자·도메인별 가치 함수를 학습시키는 방향이 좋습니다.

### 2. 질문은 그래프 자산

질문을 독립된 텍스트 목록으로 저장하면 금방 묻힙니다. 다음 구조의 **Inquiry Graph**가 시스템의 핵심 자산이 되어야 합니다.

- 노드: 질문, 가설, 주장, 증거, 데이터셋, 개념, 기술, 사람/조직, 실험, 결정, 결과
- 엣지: supports, contradicts, assumes, depends_on, tests, refines, generalizes, causes, enables
- 메타데이터: 생성 계보, 사용 모델, 근거 출처, 신뢰도, 신선도, 비용, 인간 평가, 후속 결과
- 버전: 질문의 초안 → 반론 반영본 → 검증 가능 형태 → 채택된 연구 과제의 계보

이 구조가 있어야 “이미 답이 난 질문”, “명백히 중복인 질문”, “같은 전제를 공유하는 질문”을 제거하고, 반대로 지식 그래프의 단절부·모순부·밀도 낮은 영역에서 새 질문을 발견할 수 있습니다.

### 3. 생성과 판정을 분리

생성 모델이 자신의 산출물을 심사하게 하면 ‘그럴듯하지만 평범한 질문’에 과대평가가 일어납니다. 따라서 **발산과 수렴을 조직적으로 분리**해야 합니다.

- 발산 단계: 역할과 모델 다양성을 극대화해 수백 개의 질문 후보를 생성
- 적대적 검증: 반례, 숨은 전제, 이미 알려진 답, 측정 불가능성, 위험성을 공격
- 수렴 단계: 질문 정규화, 중복 제거, 근거 연결, 가치 점수화, 포트폴리오 구성
- 인간 관문: 높은 영향·위험·비용의 질문만 최종 승인 또는 피드백

Google의 멀티에이전트 예시에서도 리서처·심사자·콘텐츠 역할을 나누고 반복 피드백 루프를 두며, 오케스트레이터가 정보 흐름을 관리합니다. 이 역할 분리가 InquiryFoundry에도 직접 적용됩니다. [codelabs.developers.google](https://codelabs.developers.google.com/codelabs/production-ready-ai-roadshow/1-building-a-multi-agent-system/building-a-multi-agent-system)

## 권장 에이전트 구성

처음부터 자유형 스웜으로 시작하기보다, **중앙 통제형 오케스트레이터 + 병렬 전문가 + 심사 루프**로 시작해야 합니다. 오케스트레이터는 인텐트 라우팅, 상태·문맥 유지, 에이전트 수명주기와 요청 흐름을 통합 관리하는 제어면(control plane) 역할을 맡습니다. [arxiv](https://arxiv.org/html/2601.13671v1)

| 계층 | 에이전트 | 핵심 역할 | 주요 산출물 |
|---|---|---|---|
| 제어 | Inquiry Director | 목표 분해, 작업 예산, 라우팅, 종료 판단 | 실행 DAG, 최종 질문 포트폴리오 |
| 입력 해석 | Context Cartographer | 문서·데이터·사용자 의도에서 개념·주장·제약 추출 | 문제 지형도 |
| 조사 | Evidence Scout | 웹, 논문, 특허, 코드, 내부 지식 검색 | 근거 묶음·출처 그래프 |
| 발산 | First-Principles Inquirer | 기본 전제와 인과 구조 재질문 | 전제해체 질문 |
| 발산 | Cross-Domain Synthesizer | 이종 산업·학문·기술의 구조적 유사성 탐색 | 교차영역 질문 |
| 발산 | Future/Scenario Agent | 시간축·기술 성숙도·2차 효과를 전개 | 미래 시나리오 질문 |
| 발산 | Constraint Reverser | “제약을 제거/반전하면?”을 탐색 | 역발상 질문 |
| 검증 | Contrarian Red Team | 숨은 가정, 반례, 위험·악용 가능성 공격 | 반론·위험 질문 |
| 검증 | Prior-Art / Duplicate Hunter | 기존 연구·특허·시장 제품과 비교 | 신규성·중복 판정 |
| 검증 | Falsifiability Engineer | 질문을 관찰·실험·지표 형태로 변환 | 검증 프로토콜 |
| 판정 | Question Judge Ensemble | 가치 함수 평가 및 순위 앙상블 | 점수·근거·불확실성 |
| 학습 | Outcome Learner | 채택·실험·성과 피드백을 반영 | 가중치·정책 업데이트 |

다중 데이터 소스에서는 질의 유형에 따라 RAG, SQL, 전문 도구를 동적으로 선택하는 라우팅이 정확도와 맥락 적합성을 높일 수 있습니다. InquiryFoundry도 “질문 생성” 이전에 무엇을 검색·계산·시뮬레이션해야 하는지를 분류하는 라우터가 필요합니다. [themoonlight](https://www.themoonlight.io/ko/review/dynamic-multi-agent-orchestration-and-retrieval-for-multi-source-question-answer-systems-using-large-language-models)

## 질문 생산 파이프라인

### 1. Inquiry Brief 정규화

사용자에게 “무엇에 관해 질문을 만들까?”만 묻지 말고 구조화된 입력을 받으세요.

- 탐구 대상: 기술, 산업, 과학 현상, 조직 문제, 정책, 데이터셋
- 목표: 발견, 검증, 전략, 위험 탐지, 발명, 학습
- 시간 축: 현재, 1년, 5년, 장기 불확실성
- 제약: 예산, 데이터 접근성, 윤리, 보안, 규제
- 금지된 전제와 반드시 고려할 관점
- 성공 기준: 논문 주제, 실험 설계, 투자 판단, 제품 로드맵 등

예를 들어 사용자가 “양자-AI 하이브리드 오케스트레이션”을 넣으면, 시스템은 “양자컴퓨터로 LLM을 더 빠르게 할 수 있는가?” 같은 평범한 질문이 아니라 아래 질문을 지향해야 합니다.

> “오케스트레이터의 작업 배분이 조합최적화 문제일 때, 양자 가속의 이득이 실제로 나타나는 에이전트 수·작업 의존성·오류율의 경계 조건은 무엇인가?”

이 질문은 대상, 작동 메커니즘, 측정 변수, 반증 가능성까지 포함합니다.

### 2. 지식 지형화와 빈 공간 탐색

- 문서·논문·특허·뉴스·코드·내부 노트에서 주장-근거-가정 그래프 추출
- 시간별 기술 변화와 인접 분야의 개념 이동을 추적
- 상충되는 주장, 근거 없는 중심 주장, 과도하게 반복되는 질문, 연결되지 않은 클러스터 식별
- “이미 많이 답한 질문”을 패널티하고 “중요하지만 증거가 부족한 질문”을 우선 탐색

### 3. 질문 렌즈를 통한 병렬 발산

모든 주제에 동일한 프롬프트를 적용하지 말고, **질문 문법(question grammar)**을 제품의 핵심 IP로 관리해야 합니다.

- 전제 렌즈: “이 문제의 암묵적 가정은 무엇이며, 틀리면 무엇이 바뀌는가?”
- 인과 렌즈: “A와 B의 상관을 만드는 숨은 변수가 있는가?”
- 경계조건 렌즈: “이 결론은 어느 조건에서 더 이상 성립하지 않는가?”
- 반사실 렌즈: “핵심 제약이 사라지거나 반대가 되면 무엇이 가능한가?”
- 조합 렌즈: “X의 구조를 Y에 이식하면 어떤 새 질문이 생기는가?”
- 시간 렌즈: “기술·비용·규제가 10배 변하면 어떤 질문이 중요해지는가?”
- 측정 렌즈: “현재 KPI가 포착하지 못해 최적화를 왜곡하는 변수는 무엇인가?”
- 윤리·안전 렌즈: “누가 비용을 부담하고, 어떤 악용 경로가 생기는가?”

### 4. 적대적 정제와 검증 설계

각 후보에 아래 검증을 수행합니다.

- 이미 답이 알려진 질문인가?
- 용어가 모호하거나 답이 정의에 의해 결정되는가?
- 답이 달라져도 행동·결정이 바뀌지 않는가?
- 관찰, 실험, 시뮬레이션, 데이터 분석으로 반증 가능한가?
- 전제가 사실인가? 출처가 있는가?
- 정보 위해, 개인정보, 편향 증폭, 지식재산권 위험이 있는가?

마지막에 질문 하나만 출력하지 말고, **질문 + 왜 지금 중요한가 + 전제 + 근거 + 반론 + 검증 방법 + 예상 비용 + 다음 액션**을 하나의 “Inquiry Card”로 출력해야 합니다.

## 기술 아키텍처

```text
[UI / CLI / API]
        │
[Inquiry Brief Compiler]
        │
[Orchestrator / Policy Engine] ── [Agent Registry + Capability Router]
        │                                   │
        ├── [Research & Retrieval Mesh] ────┤
        ├── [Question Generation Ensemble] ─┤
        ├── [Red Team / Judge Ensemble] ────┤
        └── [Experiment Planner] ───────────┘
        │
[Inquiry Graph + Evidence Store + Vector / Keyword Retrieval]
        │
[Evaluation, Provenance, Observability, Feedback Learning]
```

구현 관점에서는 다음이 중요합니다.

- **상태 모델:** 이벤트 소싱 기반의 실행 로그와 버전 관리 블랙보드. 에이전트 간 상호작용과 중간 산출물은 재현 가능해야 합니다
- **프로토콜:** 내부적으로는 typed message schema, 외부·원격 에이전트에는 MCP/A2A 어댑터
- **모델 라우팅:** 창의적 발산에는 서로 상이한 모델군, 사실 확인에는 검색·도구 사용에 강한 모델, 판정에는 독립 모델 앙상블
- **메모리 분리:** 세션 컨텍스트, 장기 사용자/조직 메모리, 증거 저장소, 실행 메모리를 혼합하지 않기
- **관측성:** 질문 ID 단위로 에이전트 호출, 모델, 프롬프트 버전, 도구 결과, 비용, 지연, 인용, 점수 변화를 추적
- **복구:** 타임아웃, 재시도, 서킷 브레이커, 실패 작업 큐, 부분 결과 반환

운영형 멀티에이전트 시스템에는 분산 추적, 비용 귀속, 버전 관리된 블랙보드 리플레이가 필수라는 실무적 지적이 있습니다. 또한 하나의 패턴에 고정하기보다 문제에 맞게 오케스트레이터-워커, 팬아웃, 계층형, 메쉬를 조합하는 접근이 권장됩니다. [glukhov](https://www.glukhov.org/ko/ai-systems/architecture/multi-agent-orchestration-patterns/)

## 평가와 학습

### 오프라인 벤치마크

초기에는 세 부류의 과제를 만드세요.

- **Known frontier:** 이미 중요한 질문이 알려진 분야에서 그 질문 또는 동등한 질문을 재발견하는가
- **Open frontier:** 최신 기술·과학 분야에서 전문가가 신규성·가치·검증 가능성을 평가하는가
- **Decision impact:** 실제 팀이 질문을 받고 조사·실험·제품 결정을 바꿨는가

질문 품질의 평가는 반드시 인간 전문가 평가와 실제 결과를 포함해야 합니다. LLM-as-a-judge만으로는 자기강화형 편향이 생길 수 있습니다.

### 온라인 핵심 지표

- 채택률: 생성 질문 중 인간이 저장·수정·추적한 비율
- 후속행동률: 실험, 조사, 이슈, 설계 문서로 이어진 비율
- 결정변화율: 기존 로드맵·가설·투자 판단을 바꾼 비율
- 시간당 가치: 사용자 검토 시간 대비 채택 질문의 영향 점수
- 신규성 정밀도: 전문가가 “이전에는 고려하지 않았다”고 판정한 비율
- 중복률·환각 전제율·근거 없는 질문 비율
- 질문당 비용·지연 시간·재현 성공률

가장 강력한 방어력은 “질문 생성 모델”이 아니라 **질문 → 검증 → 결과 → 가치 학습**의 폐루프 데이터입니다.

## 출시 전략과 예측

### 첫 번째 웨지

범용 소비자 서비스로 시작하지 말고, 질문의 경제적 가치가 명확하고 사용자가 피드백을 줄 수 있는 좁은 도메인을 택하는 것이 좋습니다.

- AI 시스템 아키텍처·에이전트 연구팀
- 딥테크 R&D 및 특허 전략팀
- 전략 컨설팅·투자 리서치
- 연구 중심 대학원·랩
- 규제·안전·사이버·국방과 같이 “놓친 질문”의 비용이 큰 분야

당신의 배경을 고려하면 1차 웨지는 **AI 에이전트/양자-AI/산업 자동화 연구를 위한 Frontier Inquiry Copilot**이 자연스럽습니다. 여기서 기술 구조, 실험 설계, 안전성, 시장화 간의 충돌을 질문 그래프로 축적하면 차별화된 초기 데이터 자산이 생깁니다.

### 0~6개월 MVP

- 단일 도메인, 단일 팀, 5~8개 고정 역할 에이전트
- 문서 업로드 + 웹/논문 검색 + Inquiry Card 생성
- 질문 그래프의 최소 구현: 질문-증거-가설-결과 연결
- 인간의 `save / reject / revise / investigate` 피드백
- 주간 “새로 떠오른 핵심 질문” 리포트
- 비용 상한, 인용 강제, 감사 로그, 재현 실행

처음부터 완전 자율 스웜을 만들지 않는 것이 중요합니다. 단일 에이전트에서 시작해 필요한 복잡도에서 멀티에이전트로 확장하고, 중앙 제어가 필요한 경우 계층형 패턴을 사용하라는 실무 권고와도 맞습니다. [youngju](https://www.youngju.dev/blog/ai-platform/2026-03-14-ai-agent-multi-agent-orchestration-patterns.en)

### 6~18개월 확장

- 도메인별 Question Grammar 및 평가 루브릭 마켓플레이스
- 에이전트 간 토론·반대 심문·가설 토너먼트
- 특허, 논문, 코드, 기업 데이터와 연결한 evidence-first 질문
- 실험 설계·시뮬레이션·코드 생성으로 이어지는 closed loop
- 조직별 프라이빗 Inquiry Graph와 권한·출처 격리
- “질문 포트폴리오” 대시보드: 중요도 × 불확실성 × 검증비용 × 전략적 시급성

### 장기 예측

1. 범용 답변은 점점 저렴해지고, **무엇을 물을지 결정하는 능력**과 검증 우선순위화가 더 희소해질 가능성이 큽니다.  
2. 단일 모델의 독창성보다, 상이한 모델·도구·데이터·역할 간의 **생산적 불일치**를 설계하는 오케스트레이션이 경쟁력이 됩니다.  
3. 질문 생성 그 자체는 빠르게 범용 기능이 되므로, 장기 해자는 질문 그래프, 평가 결과, 후속 실행 데이터, 도메인별 질문 문법, 신뢰 가능한 출처 계보가 됩니다.  
4. 기업 고객은 ‘창의성’보다 **근거·감사 가능성·보안·재현성**을 구매하게 됩니다. 따라서 관측성과 provenance는 부가기능이 아니라 코어 기능입니다. Microsoft의 멀티에이전트 참조 아키텍처도 툴 어댑터, 보안 게이트웨이, 요청 라우터, 모니터링을 별도 핵심 구성요소로 둡니다. [microsoft.github](https://microsoft.github.io/multi-agent-reference-architecture/docs/reference-architecture/Reference-Architecture.html)

## 가장 중요한 선택

InquiryFoundry가 성공하려면 “AI가 질문을 잘 만든다”를 증명하려 하지 말고, 다음을 증명해야 합니다.

> **InquiryFoundry가 만든 질문이 인간 팀이 원래 놓쳤을 중요한 불확실성을 드러내고, 더 빠르고 더 좋은 연구·실험·제품·전략 행동으로 연결한다.**

그 기준을 제품의 데이터 모델, 평가 체계, UI, 가격 정책, 고객 성공 지표 전부에 관통시키는 것이 가장 중요합니다.


# ===========================================
# AI Agent 8


# InquiryFoundry: 다종 AI 에이전트 기반 질문 생산 시스템의 핵심 요소 분석과 예측

> **한 줄 요약**  
> InquiryFoundry의 성패는 “좋은 답변을 만드는 LLM”을 쓰는가가 아니라, **서로 다른 지식·관점·반론을 가진 에이전트들이 증거 기반으로 충돌하고, 그 결과물을 검증 가능하고 행동 가능한 질문으로 정제하는 오케스트레이션·평가·기억·거버넌스 구조를 얼마나 잘 설계했는가**에 달려 있습니다.

아래는 공개된 AI 연구·산업·에이전트 설계 동향을 바탕으로, InquiryFoundry에 필요한 요소를 **수집 신호 → 분석 → 예측 → 실행 제안** 순서로 정리한 것입니다.

---

## 1. 정보 수집 관점: 어떤 신호를 봐야 하는가?

InquiryFoundry를 설계하려면 다음 영역의 정보를 수집하고 해석해야 합니다.

| 수집 영역 | 주요 신호 | InquiryFoundry에 대한 시사점 |
|---|---|---|
| 생성형 AI 질문 생성 | 답변보다 문제 정의, research ideation, hypothesis generation에 대한 관심 증가 | AI의 역할을 “답변자”에서 “질문 설계자”로 전환해야 함 |
| 멀티에이전트 시스템 | debate, role-play, critic-agent, verifier-agent, red-teaming | 단일 에이전트는 편향과 환각에 취약하므로 구조화된 다종 에이전트가 필요 |
| RAG·지식 그래프 | 검색 증강 생성, 인용 추적, 증거 기반 답변, provenance 요구 증가 | 질문도 “근거 없는 창의성”이 아니라 지식·증거·불확실성에 기반해야 함 |
| 평가 시스템 | LLM-as-judge, human evaluation, benchmark, calibration | 질문의 novelty, validity, actionability를 측정하는 평가 루프가 핵심 |
| 의사결정·연구개발 | decision intelligence, scenario planning, foresight, innovation pipeline | 질문은 연구·실험·투자·정책 결정으로 연결되어야 가치가 생김 |
| AI 안전·거버넌스 | hallucination, bias, dual-use, prompt injection, auditability | 질문 생산도 안전성, 책임성, 추적 가능성, 인간 통제를 내장해야 함 |

---

## 2. 분석: InquiryFoundry의 핵심 설계 원리

### 2.1 “좋은 질문”의 정의부터 명확해야 함

InquiryFoundry가 생산해야 할 질문은 단순히 새로운 문장이 아니라, **새로운 탐구 경로를 열고, 검증 가능하며, 행동으로 전환될 수 있는 질문**입니다.

다음 공식으로 개념화할 수 있습니다.

```text
질문의 가치
= 신규성 × 중요성 × 검증가능성 × 행동가능성 × 안전성 × 증거기반성
```

| 기준 | 의미 | 설계 반영 |
|---|---|---|
| **신규성** | 기존 질문과 개념적으로 중복되지 않는가? | 기존 질문 코퍼스와의 의미적 거리, 지식 그래프상 새로운 경로 탐지 |
| **중요성** | 그 질문이 해결되면 어떤 불확실성·비용·기회가 달라지는가? | 영향도, 이해관계자, 의사결정 연계성 평가 |
| **검증가능성** | 가설, 데이터, 실험, 관찰 가능 여부로 변환 가능한가? | testability, falsifiability, evidence path 명시 |
| **행동가능성** | 다음 실험·조사·파일럿·의사결정으로 연결되는가? | next action, owner, resource, timeframe 제안 |
| **안전성** | 윤리·법률·사회·보안 리스크를 유발하지 않는가? | safety reviewer, dual-use filter |
| **증거기반성** | 근거 없는 추측이 아니라 지식·데이터·인용에 기반하는가? | source citation, confidence, uncertainty metadata |

---

## 3. InquiryFoundry의 핵심 요소

InquiryFoundry는 크게 다음 6개 층위로 설계할 수 있습니다.

```text
1. 지식·신호 수집층
2. 질문 생성 에이전트층
3. 오케스트레이션·토론층
4. 검증·평가층
5. 행동 연결·피드백층
6. 기억·거버넌스·운영층
```

---

# 3.1 지식·신호 수집층

질문의 품질은 원료 지식의 품질에 의해 제한됩니다. 따라서 “질문을 만들기 위한 지식 기반”이 먼저 필요합니다.

## 핵심 구성 요소

### 1) 멀티소스 지식 수집
수집 대상은 단순 문서가 아니라, **사실·가정·이해관계·불확실성·이상 신호**를 포함해야 합니다.

예:

| 지식 유형 | 예시 |
|---|---|
| 학술 지식 | 논문, 리뷰, 인용 네트워크, 연구 공백 |
| 기술 지식 | 특허, 기술 문서, API 명세, 표준 |
| 시장·산업 신호 | 뉴스, 투자 동향, 규제 변화, 기업 전략 |
| 사용자·사회 신호 | 커뮤니티, 리뷰, 민원, 정책 논쟁 |
| 내부 지식 | 회의록, 의사결정 기록, 실패 사례, 실험 로그 |
| 미래 신호 | 약신호, 이상치, 시나리오, 규제 예고 |
| 메타 지식 | 불확실성, 신뢰도, 시점, 출처, 반론 |

### 2) 지식 그래프 + 벡터 검색
단순 RAG만으로는 “새로운 질문”을 만들기 어렵습니다. 개념 간 관계, 모순, 시간 변화, 불확실성을 표현해야 합니다.

권장 구조:

```text
Vector Store
- 의미 유사도 검색
- 유사 질문 탐지
- 기존 담론과의 거리 측정

Knowledge Graph
- 개념-개념 관계
- 증거-주장 연결
- 시간별 변화
- 모순·충돌·공백 탐지

Evidence Index
- 출처, 신뢰도, 날짜, 인용 관계
- 주장별 찬반 증거 매핑
```

### 3) 불확실성 메타데이터
모든 지식에는 다음을 붙여야 합니다.

```text
- confidence score
- evidence strength
- temporal validity
- source reliability
- contradiction flag
- unknown / missing flag
```

이것이 있어야 AI가 “모르는 것”을 질문으로 전환할 수 있습니다.

---

# 3.2 질문 생성 에이전트층

단일 LLM에게 “새로운 질문을 만들어 달라”고 하면 대체로 기존 담론을 재조합하거나, 겉으로만 새롭고 실질적으로는 진부한 질문을 만들기 쉽습니다. 따라서 **서로 다른 인지 역할을 가진 에이전트**가 필요합니다.

## 핵심 에이전트 역할

| 에이전트 | 역할 | 질문 생산 기여 |
|---|---|---|
| **Signal Scout** | 뉴스, 논문, 특허, 규제, 이상 신호 수집 | 새로운 변화와 약신호를 질문의 원료로 전환 |
| **Knowledge Curator** | 증거 정리, 출처 신뢰도 평가 | 질문이 근거 없는 공상이 되지 않도록 방지 |
| **Assumption Auditor** | 암묵적 전제, 고정관념, 당연시되는 조건 발굴 | “왜 우리는 이렇게 가정하는가?”라는 질문 생성 |
| **Analogist** | 다른 분야·산업·시대의 유사 구조를 이식 | 학제간 전이 질문 생성 |
| **Contrarian / Red Team** | 합의, 유행, 직관에 반론 제기 | 반박 가능하고 강한 질문 생성 |
| **Futurist / Scenario Agent** | 미래 시나리오, 규제 변화, 기술 확산 가정 | 선제적 질문, what-if 질문 생성 |
| **Ethicist / Safety Agent** | 가치 충돌, 사회적 영향, 악용 가능성 점검 | 책임 있는 질문과 금지·보완 필요 질문 선별 |
| **Feasibility Engineer** | 데이터, 예산, 기술, 시간 관점에서 실행 가능성 평가 | 질문을 실험·파일럿·조사로 바꾸기 쉽게 만듦 |
| **Question Composer** | 여러 에이전트의 출력을 질문 카드 형태로 정제 | 질문을 명확하고 평가 가능하게 표현 |
| **Verifier / Critic** | 논리 오류, 중복성, 증거 부족 검사 | 질문의 품질과 검증 가능성 향상 |
| **Orchestrator** | 전체 흐름, 충돌 조정, 우선순위 관리 | 다종 에이전트 생산성을 통제 |
| **Human Facilitator** | 최종 판단, 도메인 맥락, 책임 있는 선택 | 인간 통제를 유지하고 질문의 실제 가치 판별 |

---

# 3.3 오케스트레이션·토론층

멀티에이전트 시스템에서 중요한 것은 단순히 에이전트를 많이 두는 것이 아니라, **어떻게 충돌하고 수렴하는가**입니다.

## 권장 오케스트레이션 패턴

```text
1. Brief Intake
   - 도메인, 목적, 제약, 의사결정 맥락 입력

2. Knowledge Mapping
   - 관련 개념, 증거, 이해관계자, 기존 질문 수집

3. Assumption Mining
   - 암묵적 전제와 당연시되는 조건 추출

4. Divergent Question Generation
   - 각 에이전트가 독립적으로 질문 초안 생성

5. Cross-Examination
   - 반박, 대체 관점, 증거 부족, 위험성 검토

6. Prior Art / Novelty Check
   - 기존 질문·연구·특허·담론과 비교

7. Convergence
   - 질문 카드 형태로 통합 및 우선순위화

8. Human Review
   - 전문가 판단, 맥락 보정, 채택 여부 결정

9. Action Packaging
   - 실험 설계, 데이터 요구사항, 다음 단계 제안

10. Feedback Loop
   - 실제 결과와 피드백을 기억층에 저장
```

## 중요한 설계 원칙

### 1) 독립 생성 후 토론
에이전트들이 처음부터 같은 컨텍스트에 몰리면 동조화될 수 있습니다. 따라서 각 에이전트는 먼저 독립적으로 질문을 생성한 뒤 상호 검토해야 합니다.

### 2) 구조화된 반론
단순히 “비판해 줘”가 아니라 다음을 요구해야 합니다.

```text
- 이 질문이 놓친 이해관계자는?
- 어떤 증거가 부족한가?
- 어떤 전제가 의심되는가?
- 반대로 질문한다면?
- 이미 존재하는 질문과 무엇이 다른가?
- 행동으로 옮기기 어려운 이유는?
```

### 3) 소수의견 보존
합의만 추구하면 혁신적 질문이 사라질 수 있습니다. 따라서 **minority report**, **dissent log**, **high-risk high-novelty bucket**을 유지해야 합니다.

### 4) 질문 유형별 분리
모든 질문을 같은 방식으로 다루면 안 됩니다.

| 질문 유형 | 예시 |
|---|---|
| 현상 규명 | “왜 이런 사용자 행동 변화가 발생하는가?” |
| 원인 진단 | “어떤 기술·제도적 요인이 이 병목을 만드는가?” |
| 가정 전복 | “이 문제는 반드시 인간 전문가가 판단해야 하는가?” |
| 미래 시나리오 | “규제가 X 방향으로 바뀌면 어떤 시장이 재정의되는가?” |
| 설계·대안 | “기존 데이터 없이 이 문제를 해결할 다른 방법은?” |
| 규범·가치 | “이 기술은 누구의 선택권을 제한하는가?” |
| 메타 질문 | “우리가 풀고 있다고 믿는 문제는 실제로 맞는 문제인가?” |

---

# 3.4 검증·평가층

InquiryFoundry의 핵심 차별점은 **질문을 평가하고 검증하는 시스템**입니다. 질문 생산보다 더 중요한 것이 질문 선별입니다.

## 질문 평가 기준

### 1) 신규성 Novelty
단순한 문장 차이가 아니라 개념적 신규성이어야 합니다.

평가 방법:

```text
- 기존 질문 코퍼스와 embedding 유사도 비교
- 지식 그래프상 새로운 개념 경로 존재 여부
- 기존 논문·특허·회의록에서의 유사 질문 검색
- 전문가 기반 prior art review
```

주의할 점:
- 유사도가 낮다고 좋은 질문은 아님
- 지나치게 낯설고 검증 불가능한 질문은 가치가 낮을 수 있음
- “익숙한 문제의 낯선 재정의”가 더 가치 있을 수 있음

### 2) 타당성 Validity
질문이 논리적·사실적으로 성립하는지 평가합니다.

```text
- 근거 없는 단정을 포함하지 않는가?
- 잘못된 전제를 포함하지 않는가?
- 개념 정의가 명확한가?
- 관련 증거가 존재하는가?
- 반례가 이미 존재하지 않는가?
```

### 3) 검증가능성 Testability
질문이 가설, 데이터, 실험, 관찰로 전환될 수 있어야 합니다.

```text
- 어떤 데이터로 답할 수 있는가?
- 어떤 실험이 가능한가?
- 어떤 지표가 개선 여부를 알려주는가?
- 어떤 결과가 나오면 질문이 반증되는가?
```

### 4) 행동가능성 Actionability
질문이 다음 행동으로 연결되어야 합니다.

```text
- 다음 실험은 무엇인가?
- 어떤 파일럿을 할 수 있는가?
- 어떤 의사결정에 영향을 주는가?
- 누가 실행할 수 있는가?
- 시간과 예산은 현실적인가?
```

### 5) 영향력 Impact
질문이 풀렸을 때 줄어드는 불확실성, 비용, 위험 또는 창출되는 기회가 커야 합니다.

```text
- 해결 시 어떤 의사결정이 달라지는가?
- 어떤 병목이 해소되는가?
- 어떤 신규 시장·연구 영역이 열리는가?
- 어떤 리스크를 조기에 발견할 수 있는가?
```

### 6) 안전성 Safety
질문 자체가 악용 가능성, 차별, 프라이버시, 안보 리스크를 유발하지 않는지 평가해야 합니다.

```text
- dual-use 가능성
- 개인정보 침해 가능성
- 사회적 편향 강화 가능성
- 규제 위반 가능성
- 이해관계자 피해 가능성
```

---

## 질문 평가 점수 예시

```text
Question Score =
  0.20 × Novelty
+ 0.20 × Impact
+ 0.20 × Testability
+ 0.15 × Actionability
+ 0.10 × Evidence Grounding
+ 0.10 × Safety
+ 0.05 × Diversity / Strategic Fit
```

단, 점수는 절대화하면 안 되고 **도메인과 목적에 따라 가중치를 조정**해야 합니다.

---

# 3.5 행동 연결·피드백층

질문이 “좋은 질문”으로 끝나면 시스템은 실패합니다. 질문은 반드시 다음 단계로 연결되어야 합니다.

## 질문 카드 표준

각 질문은 다음 구조로 저장하는 것이 좋습니다.

```yaml
question_id: Q-2026-0001
question: "..."
context: "..."
why_new: "..."
assumptions_challenged:
  - "..."
evidence:
  - source: "..."
    claim: "..."
    confidence: "..."
hypothesis_if_answered: "..."
test_method:
  - experiment: "..."
  - data_needed: "..."
  - metric: "..."
success_criteria: "..."
failure_criteria: "..."
action_options:
  - "..."
risks:
  - "..."
ethical_flags:
  - "..."
impact_score: 0.0
novelty_score: 0.0
testability_score: 0.0
human_review_status: "pending"
dissent_notes:
  - "..."
next_owner: "..."
```

## 질문에서 행동으로의 전환 경로

```text
Question
→ Hypothesis
→ Evidence requirement
→ Experiment / Pilot / Survey / Simulation
→ Result
→ Updated knowledge graph
→ New question generation
```

이 루프가 쌓일수록 InquiryFoundry는 단순 질문 생성기가 아니라 **조직의 탐사·학습 엔진**이 됩니다.

---

# 3.6 기억·거버넌스·운영층

## 1) Inquiry Memory
과거에 만든 질문, 채택 여부, 실험 결과, 실패 이유를 기억해야 합니다.

기억해야 할 것:

```text
- 질문 원문
- 생성 에이전트
- 사용된 지식 출처
- 전문가 평가
- 채택/거절 이유
- 실험 결과
- 후속 질문
- 실패 패턴
```

이것이 없으면 시스템은 계속 같은 질문을 반복합니다.

## 2) Provenance와 감사 가능성
질문이 어디서 왔는지 추적 가능해야 합니다.

```text
- 어떤 문서에서 촉발되었는가?
- 어떤 에이전트가 제안했는가?
- 어떤 반론이 있었는가?
- 어떤 증거가 사용되었는가?
- 누가 최종 채택했는가?
```

## 3) 인간 통제 Human-in-the-loop
AI가 질문을 대량 생산할수록 인간의 역할은 더 중요해집니다.

인간의 역할:

```text
- 도메인 맥락 제공
- 전략적 우선순위 설정
- 윤리적 판단
- 질문 채택/폐기
- 실험 책임 부여
- 조직 내 의미 부여
```

## 4) 보안과 안전
지식 수집과 에이전트 호출 과정에서 다음을 방어해야 합니다.

```text
- prompt injection
- 오염된 문서 기반 질문 유도
- 내부 정보 유출
- 악의적 질문 생성
- 민감 데이터 노출
- 외부 API·도구 오남용
```

---

## 4. 다종 에이전트가 서로 다른 지식·관점·반론을 교차시키는 방법

InquiryFoundry의 핵심은 “다양성 있는 충돌”입니다.

### 4.1 지식 다양성
각 에이전트에게 서로 다른 지식 팩을 주입합니다.

```text
- 기술 에이전트: 논문, 특허, 코드, 표준
- 시장 에이전트: 산업 보고서, 고객 피드백, 경쟁사 동향
- 규제 에이전트: 법률, 가이드라인, 판례
- 사회문화 에이전트: 미디어, 커뮤니티, 윤리 담론
- 사용자 에이전트: 실제 사용자 언어, 불만, 작업 맥락
- 과학 에이전트: 인과관계, 실험 가능성, 통계적 한계
```

### 4.2 관점 다양성
에이전트에게 단순 페르소나가 아니라 **목표 함수**를 부여해야 합니다.

예:

```text
- 리스크 최소화 에이전트
- 속도 최대화 에이전트
- 사용자 가치 에이전트
- 과학적 엄밀성 에이전트
- 비즈니스 임팩트 에이전트
- 공공성·윤리 에이전트
```

### 4.3 반론 다양성
반론도 유형별로 분리합니다.

| 반론 유형 | 질문 |
|---|---|
| 증거 반론 | “그 주장을 뒷받침하는 데이터가 충분한가?” |
| 논리 반론 | “인과관계가 아니라 상관관계 아닌가?” |
| 전제 반론 | “그 문제는 정말 해결할 가치가 있는 문제인가?” |
| 대안 반론 | “더 간단한 질문 또는 더 근본적인 질문은 없는가?” |
| 이해관계 반론 | “누구의 이익이 과대대표되었는가?” |
| 실행 반론 | “데이터가 있어도 조직이 실행할 수 있는가?” |

---

## 5. 질문 생산 파이프라인 예시

다음은 실제 시스템에 적용 가능한 파이프라인입니다.

```text
[입력]
도메인, 목표, 제약, 이해관계자, 기존 질문 목록, 최신 신호

↓
[Step 1] Signal Extraction
- 최신 변화, 이상 신호, 규제·기술·시장 변화 추출

↓
[Step 2] Knowledge Graph Construction
- 개념, 관계, 증거, 모순, 공백 매핑

↓
[Step 3] Assumption Mining
- 당연시되는 전제 추출
- “무엇을 묻지 않고 있는가?” 식별

↓
[Step 4] Multi-Agent Independent Question Generation
- 각 에이전트가 독립적으로 질문 초안 생성

↓
[Step 5] Cross-Examination Debate
- 반론, 보완, 증거 요구, 대체 질문 제시

↓
[Step 6] Novelty & Prior Art Check
- 기존 질문·논문·특허·내부 기록과 비교

↓
[Step 7] Scoring & Clustering
- 유사 질문 통합
- novelty, impact, testability, safety 평가

↓
[Step 8] Question Card Generation
- 질문, 근거, 반론, 실험 방법, 리스크 정리

↓
[Step 9] Human Review Board
- 전문가 검토 및 채택

↓
[Step 10] Action Packaging
- 다음 실험, 파일럿, 의사결정 과제로 전환

↓
[Step 11] Feedback Memory
- 결과와 학습을 저장해 다음 질문 생성에 반영
```

---

## 6. 기술 아키텍처 제안

## 권장 구성

```text
Frontend / API
- 질문 입력
- 질문 카드 검토
- 전문가 평가 인터페이스
- 에이전트 토론 시각화

Orchestration Engine
- 에이전트 스케줄링
- 토론 라운드 관리
- 점수 기반 필터링
- 인간 승인 라우팅

Agent Layer
- 역할별 LLM 에이전트
- tool calling
- 검색, 그래프 질의, 평가 모델 호출

Knowledge Layer
- Vector DB
- Graph DB
- Document Store
- Evidence/Provenance Store

Evaluation Layer
- novelty scorer
- grounding checker
- testability scorer
- safety filter
- human review dashboard

Memory Layer
- question lineage
- feedback history
- experiment results
- failed question patterns

Governance Layer
- access control
- audit log
- safety policy
- data retention policy
```

---

## 7. 주의해야 할 실패 모드

| 실패 모드 | 증상 | 대응 |
|---|---|---|
| 질문 홍수 | 많지만 쓸모없는 질문이 대량 생성됨 | 평가 점수, 인간 검토, 질문 포트폴리오 관리 |
| 가짜 신규성 | 표현만 새롭고 개념은 중복 | prior art search, 지식 그래프 기반 novelty check |
| 환각 기반 질문 | 존재하지 않는 사실에 기반 | evidence citation, grounding score |
| 합의 편향 | 에이전트 토론 후 무난한 질문만 남음 | devil’s advocate, minority report 유지 |
| 실행 불가능한 질문 | 너무 추상적이고 검증 불가 | feasibility engineer, testability score |
| 안전 무시 | 악용 가능 질문 무분별 생성 | safety gate, red team review |
| 기억 부재 | 같은 질문 반복, 학습 없음 | inquiry memory, feedback loop |
| 인간 배제 | AI가 최종 판단을 대체 | human-in-the-loop, 책임자 지정 |
| 블랙박스화 | 왜 그 질문이 나왔는지 설명 불가 | provenance, reasoning trace, dissent log |

---

## 8. 예측: InquiryFoundry의 진화 방향

### 단기 예측: 1~2년
```text
질문 생성은 “아이디어 브레인스토밍 보조 도구”에서 시작해,
점차 연구개발·전략·정책 영역의 문제 정의 도구로 이동할 것입니다.
```

주요 변화:

- 기업과 연구조직에서 “답변 자동화”보다 “문제 정의 자동화”에 관심 증가
- RAG 기반 질문 생성이 일반화되지만, 품질 평가 부족으로 인간 전문가 의존 유지
- 질문 카드, hypothesis card, experiment brief 같은 중간 산출물이 중요해짐
- “좋은 질문”을 선별하는 평가 인터페이스가 차별화 요소로 부상

### 중기 예측: 2~4년
```text
질문 생산 시스템은 단일 도구가 아니라
조직의 탐구 포트폴리오를 관리하는 플랫폼으로 발전할 가능성이 큽니다.
```

주요 변화:

- 질문, 가설, 실험, 결과, 후속 질문이 하나의 lineage로 관리됨
- 다종 에이전트 간 peer review가 표준화됨
- 질문의 novelty와 actionability를 측정하는 벤치마크가 등장
- “질문 시장” 또는 “inquiry marketplace” 개념 가능  
  - 조직 내외부 전문가가 질문을 평가·구매·실험하는 구조
- AI가 만든 질문이 실제 연구 과제, 제품 실험, 정책 파일럿으로 연결

### 장기 예측: 5년 이상
```text
InquiryFoundry는 단순 질문 도구가 아니라
조직과 사회의 학습 속도를 높이는 탐사 지능 인프라가 될 수 있습니다.
```

주요 변화:

- AI가 과학적 발견, 제품 혁신, 정책 설계의 초기 질문을 상시 생성
- 시뮬레이션, 로봇 실험, 데이터 플랫폼과 결합해 질문→실험→학습 자동화
- “무엇을 알아야 하는가”를 자동으로 업데이트하는 dynamic knowledge OS로 발전
- 동시에 질문 조작, 가짜 신규성, 자동화된 문제 정의 남용 문제가 대두
- 질문 생성 시스템의 감사성, 출처 추적, 인간 책임이 규제·표준 이슈로 부상

---

## 9. 전략적으로 중요한 예측

### 예측 1: 답변 AI보다 질문 설계 AI가 더 높은 부가가치를 가짐
답변은 빠르게 상품화되지만, 좋은 질문은 다음을 결정합니다.

```text
- 어떤 문제를 풀 것인가?
- 어떤 실험을 할 것인가?
- 어떤 리스크를 먼저 볼 것인가?
- 어떤 시장을 재정의할 것인가?
```

따라서 InquiryFoundry의 가치는 “질문 개수”가 아니라 **의사결정과 실험의 방향을 바꾸는 질문의 비율**에 있습니다.

### 예측 2: 질문 평가 기능이 핵심 해자가 됨
누구나 질문을 만들 수 있는 시대에는 다음 능력이 희소해집니다.

```text
- 기존 질문과 무엇이 다른가?
- 왜 중요한가?
- 어떻게 검증할 수 있는가?
- 누가 행동할 수 있는가?
- 어떤 리스크가 있는가?
```

따라서 evaluation layer가 시스템의 경쟁 우위를 만듭니다.

### 예측 3: 조직은 “질문 포트폴리오”를 관리하게 됨
미래 조직은 프로젝트 포트폴리오처럼 질문 포트폴리오를 관리할 수 있습니다.

```text
- 단기 실험형 질문
- 장기 탐사형 질문
- 고위험 고보상 질문
- 규제·윤리형 질문
- 고객 가치형 질문
- 기술 전복형 질문
```

InquiryFoundry는 이 포트폴리오를 생성·평가·갱신하는 엔진이 됩니다.

### 예측 4: 인간 전문가는 사라지지 않고 재배치됨
AI가 질문 초안을 대량 생산하면 인간은 다음 역할을 더 강하게 맡게 됩니다.

```text
- 질문의 전략적 적합성 판단
- 윤리적 수용 가능성 판단
- 조직 내 책임 배분
- 실험 결과 해석
- 질문의 최종 채택과 폐기
```

---

## 10. MVP 실행 로드맵

## Phase 1: 개념 검증, 0~3개월

목표: “특정 도메인에서 질문 카드 100개 생성하고 전문가가 10개를 채택하는 루프”

필수 구성:

```text
- 도메인 문서 수집
- 기본 RAG
- 5개 핵심 에이전트
- 질문 카드 템플릿
- 전문가 평가 폼
```

추천 에이전트:

```text
1. Knowledge Curator
2. Assumption Auditor
3. Contrarian
4. Feasibility Engineer
5. Question Composer
```

핵심 산출물:

```text
- 질문 카드
- 근거 출처
- 반론 요약
- novelty / testability / actionability 점수
```

성공 기준:

```text
- 전문가가 “이 질문은 생각해 본 적 없다”고 평가하는 비율
- 채택된 질문 중 실제 실험·조사로 연결되는 비율
```

---

## Phase 2: 검증 강화, 3~9개월

목표: 질문의 신규성과 실행 가능성을 자동 평가하는 능력 향상

추가 구성:

```text
- prior art search
- 질문 중복 탐지
- knowledge graph 초안
- safety filter
- human review dashboard
- dissent log
```

핵심 기능:

```text
- 기존 질문 코퍼스 대비 유사도 분석
- 질문별 근거와 반론 추적
- 질문 클러스터링
- 고위험 질문 분리
```

성공 기준:

```text
- false novelty 감소
- 전문가 검토 시간 감소
- 질문에서 실험 설계로 전환되는 시간 감소
```

---

## Phase 3: 조직화·피드백 루프, 9~18개월

목표: 질문 생산이 일회성 이벤트가 아니라 조직의 학습 시스템으로 작동

추가 구성:

```text
- inquiry memory
- experiment result ingestion
- question lineage
- feedback-based re-ranking
- role-based access control
- audit trail
```

핵심 기능:

```text
- 과거 질문의 성과 학습
- 실패한 질문 패턴 인식
- 전략 목표와 질문 포트폴리오 정렬
- 부서별 질문 파이프라인 운영
```

성공 기준:

```text
- 질문 채택률
- 실험 전환율
- 질문 기반 의사결정 수
- 시간 대비 탐색 다양성
- 리스크 조기 발견 수
```

---

## 11. 핵심 KPI 제안

| KPI | 의미 |
|---|---|
| Expert Novelty Rate | 전문가가 신규하다고 평가한 질문 비율 |
| Actionable Question Rate | 실험·조사·의사결정으로 연결 가능한 질문 비율 |
| Experiment Conversion Rate | 채택 질문 중 실제 실험/파일럿으로 전환된 비율 |
| Time-to-Question | 주제 입력 후 검증된 질문 카드 생성까지 시간 |
| False Novelty Rate | 새로워 보이나 기존 질문과 중복된 비율 |
| Evidence Grounding Rate | 출처와 증거가 충분히 연결된 질문 비율 |
| Dissent Quality | 반론이 실제 질문 개선으로 이어진 비율 |
| Human Review Efficiency | 인간 검토 1건당 소요 시간 |
| Strategic Alignment Score | 조직 목표와의 부합도 |
| Risk Detection Rate | 조기 발견된 규제·윤리·보안 리스크 수 |
| Feedback Loop Rate | 실험 결과가 새 질문 생성에 반영된 비율 |

---

## 12. 특히 중요한 설계 원칙

### 원칙 1: 질문의 수보다 질문의 포트폴리오
무한정 많은 질문은 가치가 낮습니다. 다음 포트폴리오를 의도적으로 유지해야 합니다.

```text
- 즉시 실험 가능한 질문
- 고위험·고보상 질문
- 전제를 뒤집는 질문
- 윤리·규제 질문
- 장기 탐사 질문
```

### 원칙 2: 증거 없는 창의성은 경계
새로운 질문일수록 근거가 중요합니다. 질문은 다음을 포함해야 합니다.

```text
- 왜 지금 이 질문이 필요한가?
- 어떤 신호에서 나왔는가?
- 어떤 기존 지식과 충돌하거나 공백을 메우는가?
```

### 원칙 3: 반론은 시스템의 핵심 기능
반론은 오류 수정만이 아니라 질문의 깊이를 증가시키는 생산 장치입니다.

```text
Contrarian agent는 선택이 아니라 필수입니다.
```

### 원칙 4: 인간 승인 없이 최종화하지 않음
질문의 채택은 조직의 방향성을 바꾸므로 인간 책임이 필요합니다.

### 원칙 5: 질문의 계보를 저장
질문은 독립 객체가 아니라 다음 질문을 낳는 노드입니다.

```text
Question → Counter-question → Hypothesis → Experiment → Result → New Question
```

---

## 13. InquiryFoundry가 반드시 갖춰야 할 10가지

1. **지식 수집 계층**: 문서, 데이터, 규제, 사용자 신호, 이상 신호 수집  
2. **지식 그래프와 증거 인덱스**: 개념·관계·모순·공백·출처 추적  
3. **다종 에이전트 역할 분리**: 지식, 관점, 반론, 안전, 실행 역할 분리  
4. **구조화된 토론 오케스트레이션**: 독립 생성 → 교차 검토 → 수렴  
5. **질문 카드 표준**: 질문, 근거, 전제, 반론, 실험, 리스크 포함  
6. **질문 평가 엔진**: novelty, impact, testability, actionability, safety  
7. **인간 검토 인터페이스**: 전문가 평가, 채택/거절, 책임 배분  
8. **피드백 메모리**: 실험 결과와 실패 사례를 질문 생성에 재반영  
9. **거버넌스와 감사**: provenance, access control, safety policy  
10. **질문 포트폴리오 관리**: 단기 실험형부터 장기 탐사형까지 균형 유지  

---

## 14. 최종 결론

InquiryFoundry에서 가장 중요한 것은 “얼마나 많은 질문을 만드는가”가 아닙니다.

진짜 핵심은 다음입니다.

```text
1. 기존에 없던 질문을 만들 수 있는가?
2. 그 질문이 왜 새로운지 설명할 수 있는가?
3. 그 질문이 검증 가능한 형태로 전환되는가?
4. 그 질문이 실제 행동과 실험으로 이어지는가?
5. 그 질문이 조직의 학습과 의사결정을 개선하는가?
6. 그 과정이 투명하고 책임 있게 관리되는가?
```

따라서 InquiryFoundry는 단순한 AI 질문 생성기가 아니라, 다음 기능을 결합한 **다중 에이전트 탐사 지능 시스템**으로 설계해야 합니다.

```text
지식 수집
→ 전제 발굴
→ 관점 충돌
→ 질문 생성
→ 검증과 평가
→ 행동 전환
→ 학습 기억
```

가장 빠른 시작은 다음입니다.

```text
특정 도메인 하나를 정하고,
5~7개의 핵심 에이전트로 질문 카드를 생성하게 한 뒤,
전문가 평가를 통해 채택된 질문만 실제 실험·조사로 연결하는
작은 폐루프를 만드는 것입니다.
```

이 폐루프가 성공하면 InquiryFoundry는 조직의 문제 정의 속도를 높이는 도구를 넘어, **AI 시대의 탐사·혁신·의사결정을 위한 핵심 운영체제**로 발전할 수 있습니다.

