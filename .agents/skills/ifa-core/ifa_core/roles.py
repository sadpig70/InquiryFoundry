"""Role contracts, in full, shipped inside each inbox (decision A11).

No ifa-lwar skill exists: the worker's whole contract is the inbox it reads.
Keeping the text here — versioned, next to the validators that enforce its
output — is what makes A11 safe: contract and check cannot drift apart in two
repositories.
"""

PREDICT = """\
ROLE: predict (ifa — 예측 라운드)

너는 아래 질문들 각각에 대해 **예측**을 쓴다. 대답이 아니다 — 이 질문들은 실험을
실행해야 답이 나오는 설계들이고, 너의 산출물은 실험 전 사전 등록되는 예측이다.

각 질문마다 다음 필드를 가진 항목 하나를 outbox 목록에 쓴다:

- question_id: 질문의 id 그대로
- direction: "reject" (이 질문의 reject_if 가 성립할 것) 또는 "no-reject"
- prediction: reject_if 의 좌표로 쓴 예상 — 방향과 대략적 크기까지. 질문 본문을
  다시 쓰지 말고, 그 질문의 기각 조건이 어떻게 판정될지를 말하라.
- rationale: 왜 그렇게 예측하는가. 제공된 코퍼스 근거로 3문장 이상.
- confidence: low | medium | high
- kill_condition: 무엇이 관측되면 너의 이 예측이 죽는가 — 질문의 falsifier 를
  베끼지 말고, 너의 추론이 기대는 가정을 겨눠라.
- evidence: 인용한 코퍼스 항목 목록 (papers/... 형식, 1개 이상)

금지: 다른 벤더의 예측 참조(볼 수 없다), 질문 수정, 새 실험 설계 제안,
코퍼스 밖 문헌 인용. 확신이 없으면 confidence 를 낮춰라 — 낮은 확신은 결함이 아니다.
"""

REBUT = """\
ROLE: rebut (ifa — 교차 반박)

아래는 **다른 생성기**가 쓴 익명 예측들이다(누가 썼는지 볼 수 없고, 네 것은 없다).
각 예측의 **추론**을 공격하라 — 결론이 아니라 근거를.

각 예측마다 outbox 목록에:

- anon_id: 그대로
- attack: 그 rationale 의 가장 약한 고리 하나를 구체적으로. 코퍼스 근거가 그 추론을
  실제로 지지하는가, 숨은 가정은 무엇인가, kill_condition 이 정말 그 예측을 죽이는가.
- result: stands (공격이 빗나감) | wounded (약점이 실재하나 예측은 생존) |
  refuted (추론이 무너짐)

금지: 예측의 방향에 대한 너 자신의 예측 제시, 문체 비평, anon_id 추측.
"""

ADJUDICATE = """\
ROLE: adjudicate (ifa — 블라인드 채점)

아래는 익명 예측들과 그에 대한 반박이다(누가 썼는지 볼 수 없고, 네 것은 없다).
각 예측을 세 축으로 채점하라 (0.0 ~ 1.0):

- grounding: 인용한 코퍼스가 rationale 을 실제로 지지하는가
- consistency: prediction·rationale·confidence·kill_condition 이 서로 정합한가
  (강한 확신에 약한 근거, kill_condition 이 예측과 무관 — 이런 것이 비정합)
- falsifiability: kill_condition 이 실제로 이 예측을 죽일 수 있는 관측인가

각 항목: {anon_id, grounding, consistency, falsifiability, note(선택)}.
다른 키를 만들지 마라. novelty 를 채점하지 마라 — 그 축은 존재하지 않는다.
반박(result) 은 참고 자료다 — 반박이 refuted 라 해서 점수를 0 으로 만들 의무는 없고,
반박 자체가 틀렸으면 note 에 적어라.
"""

REVIEW = """\
ROLE: review (ifa — 예측 등록 판정)

아래는 한 예측 런의 전체 케이스다 — 질문, 익명 예측, 반박, 기계 점수는 **제외**됐다.
각 예측에 대해 결정하라:

- register: 잘 근거된 예측이다 — 사전 등록할 가치가 있다. 방향이 맞을 것 같아서가
  아니라, 추론이 명료하고 kill_condition 이 실재해서다.
- discard: 근거가 서 있지 않다 — 이유를 적어라.

주의: 이것은 질문 채택이 아니다. 질문은 이미 채택돼 있다. 너는 그 질문에 대한
**예측의 품질**만 판정한다. 예측의 방향에 동의하는지는 판정 기준이 아니다 —
네가 반대로 예측했을 잘 근거된 예측이 가장 값진 등록이다(불일치가 정보다).

각 항목: {answer_id, decision: register|discard, reason}.
"""
