OPERATORS = [
    ("OP-CONTRA", "A와 B가 동시에 참일 수 없는 이유는?"),
    ("OP-INVERT", "A의 핵심 가정이 거짓이면 무엇이 일어나는가?"),
    ("OP-BOUND", "A는 어떤 조건에서 더 이상 성립하지 않는가?"),
    ("OP-SCALE", "A가 규모 1000배가 되면 어떤 새 현상이 나타나는가?"),
    ("OP-XDOM", "타 영역 원리를 A에 적용하면?"),
    ("OP-MISSVAR", "현재 설명이 빠뜨린 변수는?"),
    ("OP-CAUSAL", "A-B 상관을 만드는 실제 원인은?"),
    ("OP-MEASURE", "A를 잘못 측정하고 있지는 않은가?"),
    ("OP-CF", "A가 없었다면 B는 발생했는가?"),
    ("OP-2ND", "A 성공의 2차 효과는?"),
    ("OP-ADV", "A를 실패시키는 가장 싼 방법은?"),
    ("OP-REGIME", "환경이 바뀌면 기존 규칙은 언제 역전되는가?"),
]
OPERATOR_IDS = [op for op, _ in OPERATORS]

QUESTION_CLASSES = ["phenomenon", "cause", "scenario", "design", "normative", "meta"]
UNKNOWN_TYPES = [
    "known_unknown", "contradictory", "hidden_assumption", "measurement",
    "causal", "boundary", "cross_domain_gap", "temporal", "emergent",
    "unknown_unknown_candidate",
]
MVP_UNKNOWN = {"known_unknown", "contradictory"}
EVIDENCE_KINDS = ["papers", "patents", "code", "news", "failures", "regulation", "history"]
OBJECTIVES = ["importance_max", "consensus_falsify", "info_per_cost"]
Q_STATUSES = [
    "DRAFT", "SCORED", "REVIEWED",
    "ADOPTED", "REJECTED", "DEFERRED", "MERGED", "DORMANT", "QUARANTINE",
]
DISSENT_TYPES = ["evidence", "logic", "premise", "alternative", "stakeholder", "execution"]
ATTACK_RESULTS = ["miss", "wound", "kill"]
ROLES = ["generate", "contrarian", "judge", "review"]
PHASES = {"generate": "EXPLORE", "contrarian": "EXPLOIT", "judge": "EXPLOIT",
          "review": "REVIEW"}
# A reviewer recommends; it never decides. `close` still refuses a review.yaml
# with an empty `reviewer`, so a machine recommendation cannot close a run —
# a person has to put their name on it. See REVIEWER_KINDS.
REVIEWER_KINDS = ["human", "machine_recommended", "human_ratified", "delegated"]
# What a verdict is about. `question_defect` is a property of the question and
# is fed forward as an avoid_pattern; `our_capacity` is a fact about this
# installation — a cluster we do not own, a budget we do not have — and must
# not teach the generator anything. IF produces questions; whether we can run
# one is a separate matter, and DEFERRED is where that lives.
REASON_KINDS = ["question_defect", "our_capacity"]
RUN_MODES = ["normal", "ablation"]
GOALS = ["discovery", "validation", "strategy", "risk", "invention"]
METHODS = ["observe", "experiment", "data", "simulation"]

MECH = ("G-GROUND", "G-CLEAR", "G-PATH", "G-TESTSHAPE")
HUMAN = ("G-DUP", "G-UNKNOWN", "G-ACTION", "G-SAFETY")

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

FAMILY_NORM = {
    "claude": "anthropic", "anthropic": "anthropic",
    "gpt": "openai", "openai": "openai",
    "gemini": "google", "google": "google",
    "grok": "xai", "xai": "xai",
    "deepseek": "deepseek",
    "kimi": "moonshot", "moonshot": "moonshot",
    "qwen": "alibaba", "alibaba": "alibaba",
}

NEGATION_CUES = ("아니", "않다", "반대", "모순", "불가능", "not", "cannot", "contradict", "does not", "don't")

ACCEPT_STATUS = {"succeeded"}
OMIT_STATUS = {
    "failed", "blocked", "cancelled", "interrupted", "timed_out", "protocol_error",
}

TH_MEAN = 0.40
TH_PAIR = 0.55
PRIOR_N = 50
DEFAULT_MAX_RETRIES = 2
EXCLUDE_FAMILIES = {"alibaba"}
EXCLUDE_ADAPTERS = {"qwen"}

FORBIDDEN_SCORE_KEYS = {"novelty", "diversity_contribution"}
ALLOWED_SCORE_KEYS = {"impact", "testability", "actionability", "grounding"}
PARETO_AXES = ["testability", "actionability", "grounding"]
