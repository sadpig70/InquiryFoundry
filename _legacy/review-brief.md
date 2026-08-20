---

## Q-20260820-0007 · zai(LWAR3) · OP-CAUSAL · cause

> A-B 상관을 만드는 실제 원인은? — compute-optimal parameter exponent가 Kaplan(2020)의 N ∝ C^0.73과 Hoffmann(2022)의 N ∝ C^0.5로 다르게 측정될 때, 그 차이를 만드는 원인은 LR schedule-훈련 길이 커플링과 Adam→AdamW(weight decay) 전환 중 무엇이 얼마나 설명하는가?

**왜 중요한가** — objective=info_per_cost. 지수 b는 parameter/token 예산 분배를 직접 결정하므로, 갭의 원인을 잘못 귀속하면 compute 배분 자체가 틀린다. 원인을 정확히 분해하는 것이 단위 비용당 정보를 올리는 가장 싼 경로다.

**최소 검정** — 변수 `compute-optimal 지수 b (tokenizer와 model family 고정)` · 비교 `(1) LR schedule horizon 교환 (2) Adam→AdamW 교환을 순차 적용 후 b 변화 측정` · **기각 조건 `어떤 교환에서도 갭이 유의하게 줄지 않으면 두 인과 후보 모두 기각`**
**실행 계획** — `experiment` · 두 논문의 겹치는 parameter/token grid를 tokenizer 고정 재학습한 loss 기록 · metric `각 교환이 만드는 fitting 지수 b의 개별 shift 양` · 기준 `각 교환이 갭 0.73→0.5의 최소 1/3을 설명하는지로 설명 몫을 판정`

**반증 조건** — 동일 grid에서 optimizer/schedule 조건을 하나씩 교환해도 지수가 0.73에서 유의하게 줄어들지 않으면, 이 질문의 두 인과 후보 귀속은 무효화된다.

**가정**
- 두 논문의 지수 값은 겹치는 fit 범위 안에서 비교 가능하다
- 두 측정계에서 실제로 다른 조건은 LR schedule, optimizer/weight decay, tokenizer, compute 회계로 열거 가능하다

**미지**
- 서로 다른 조건들 각각이 지수 갭 0.73→0.5에 기여하는 개별 인과 효과 크기가 분리되어 있지 않다

**근거**
- `papers/kaplan2020` (conf 0.90) — Adam과 훈련 시작 시 고정된 learning-rate schedule로 훈련하여 compute-optimal parameter scaling을 N ∝ C^0.73으로 보고했다.
- `papers/hoffmann2022` (conf 0.90) — AdamW와 훈련 길이에 맞춘 learning-rate schedule로 N ∝ C^0.5를 보고하고, LR schedule과 optimizer 차이를 기존 추정과의 갭의 주요 원인으로 지목했다.

**반론 5건** · dissent_portfolio 등재
- [`evidence`/`wound`] The precise attribution of the exponent gap to optimizer and schedule changes is stronger than the cited claims alone establish.
- [`logic`/`wound`] The causal comparison restricts attention to two candidates despite several simultaneously changed conditions.
- [`premise`/`wound`] It assumes the two exponents are comparable estimands over an overlapping regime.
- [`alternative`/`wound`] Fit-range selection could produce much of the exponent shift without either proposed training intervention being dominant.
- [`execution`/`wound`] Sequential swaps cannot identify interaction effects between schedule horizon and weight decay.

---

## Q-20260820-0009 · zai(LWAR3) · OP-CF · cause

> A가 없었다면 B는 발생했는가? — Hoffmann이 irreducible loss E를 따로 fit하지 않았다면(Kaplan식 joint fit을 그대로 썼다면), equal N-D compute-optimal 처방(N∝C^0.5, D∝C^0.5)은 여전히 도출되었는가?

**왜 중요한가** — objective=info_per_cost. equal-scaling 처방이 fitting 방법의 산물이라면 이 처방으로 모델을 선택하는 배분 전략은 검증되지 않은 방법론적 가정 위에 있다. 반사실 검증은 재분석 수준의 낮은 비용으로 이 가정을 시험할 수 있다.

**최소 검정** — 변수 `E 추정 방식 (separate fit vs joint fit)` · 비교 `동일 loss 곡선에 두 방식을 각각 적용해 compute-optimal 처방 비교` · **기각 조건 `방식과 무관하게 b가 0.5±0.05로 유지되면 'B는 A의 산물' 가설 기각`**
**실행 계획** — `simulation` · Hoffmann 표에 공개된 isoFLOP/proxy loss points · metric `두 fitting 방식의 αN, αD 쌍과 그로부터 유도되는 b의 차이` · 기준 `두 방식의 b 차이가 fit의 bootstrap 신뢰구간보다 크면 방법 의존으로 판정`

**반증 조건** — Hoffmann의 데이터를 joint fit으로 재추정해도 equal N-D 처방이 그대로 재현되면 'B가 A에 의존한다'는 반사실 전제는 무효화된다.

**가정**
- E separate fit과 joint fit 모두 공개된 loss 데이터에서 적용 가능하다
- 두 논문의 fitting 절차는 공개 표에서 재현 가능하다

**미지**
- 같은 loss 곡선을 joint fit으로 다시 얻을 때 compute-optimal 처분이 어떻게 바뀌는지

**근거**
- `papers/kaplan2020` (conf 0.80) — irreducible entropy 항을 Nc, Dc와 함께 joint fit으로 추정하고 그로부터 compute-optimal trajectory를 유도했다.
- `papers/hoffmann2022` (conf 0.85) — parametric loss L(N,D)=E+A/N^αN+B/D^αD에서 irreducible loss E를 따로 고정한 뒤 지수를 fit하여 equal N-D scaling을 유도했다.

**반론 5건** · dissent_portfolio 등재
- [`evidence`/`wound`] The claims about how irreducible loss was fixed or jointly estimated require direct procedural confirmation from the cited analyses.
- [`logic`/`wound`] Sensitivity to a fitting method would show estimator dependence, not that the equal-scaling prescription was caused solely by that method.
- [`premise`/`wound`] It assumes the published proxy-loss points identify all parameters under both fitting procedures.
- [`alternative`/`wound`] Weighting of iso-compute points and fit-range truncation may explain any recovered exponent change.
- [`execution`/`wound`] A simple bootstrap may understate uncertainty because loss points share training runs and fitted parameters are correlated.

---

## Q-20260820-0005 · openai(LWAR1) · OP-INVERT · cause

> If marginal information per training token decays with corpus redundancy, how should the compute-optimal parameter-to-token allocation change as compute grows?

**왜 중요한가** — Scaling forecasts based on raw token counts may systematically overestimate the value of additional data when marginal information decays.

**최소 검정** — 변수 `marginal mutual-information proxy per added token` · 비교 `raw-token scaling against redundancy-adjusted scaling at matched compute` · **기각 조건 `the estimated optimal parameter-to-token slope remains unchanged within preregistered uncertainty bounds`**
**실행 계획** — `data` · nested training corpora with measured semantic duplication rates · metric `change in optimal log-parameter versus log-token slope` · 기준 `slope shift exceeds the bootstrap uncertainty interval in two successive compute tiers`

**반증 조건** — The inverted premise has no operational consequence if redundancy-adjusted and raw-token allocations yield the same optimum at every compute scale.

**가정**
- Redundancy can be varied without changing tokenizer or optimizer behavior.
- Effective information density can be estimated independently of validation loss.

**미지**
- Whether declining marginal information shifts optimal compute toward parameters, curation, or neither.

**근거**
- `papers/hoffmann2022` (conf 0.81) — The estimated compute-optimal balance depends on the amount of training data supplied to each model size.
- `papers/kaplan2020` (conf 0.77) — Empirical loss scaling depends separately on dataset size and model size within the measured regime.

**반론 3건** · dissent_portfolio 등재
- [`evidence`/`wound`] 두 인용 claim은 데이터 양이 최적 배분에 영향을 준다는 배경 사실일 뿐, 여분(redundancy)에 따른 한계 정보 감소 자체를 측정한 증거가 아니다. 질문의 전제와 증거 사이에 측정 간극이 있다.
- [`alternative`/`wound`] D를 '유효 고유 토큰 수'로 재매개화하면 배분 변화가 새 현상이 아니라 재표현일 수 있다. 질문은 이 재매개화 대안을 배제하지 않았다.
- [`execution`/`wound`] minimal_test의 'marginal mutual-information proxy per added token'을 검증 손실과 독립적으로 추정해야 한다는 것이 자체 가정(#2)으로 인정되어 있다. 정보 밀도를 손실로 측정하면 순환성이 발생한다.

---

## Q-20260820-0008 · zai(LWAR3) · OP-MEASURE · phenomenon

> A를 잘못 측정하고 있지는 않은가? — training compute를 attention FLOPs와 sequence 길이 의존성을 제외한 6·N·D 근사로 측정할 때, compute-optimal frontier의 rank order와 b 추정 자체가 왜곡되는가?

**왜 중요한가** — objective=info_per_cost. FLOP 분모가 편향되면 최적처럼 보이는 배분도 proxy 하에서만 최적이다. 측정 편향의 방향과 크기가 비용 효율 판단을 직접 바꾼다.

**최소 검정** — 변수 `training token당 attention 포함 exact FLOPs` · 비교 `6ND proxy와 exact FLOPs 두 측정으로 compute-loss 평면의 rank order와 b 비교` · **기각 조건 `rank 역전이 없고 b 변화가 fit 오차 범위 내이면 측정 왜곡 가설 기각`**
**실행 계획** — `data` · 두 논문 표에 공개된 training run config와 loss 값 · metric `proxy와 exact 측정 간 rank correlation과 b 차이` · 기준 `rank correlation 0.99 초과이고 b 차이가 신뢰구간 내면 proxy를 비왜골로 판정`

**반증 조건** — exact FLOP 측정에서 frontier rank order와 b가 신뢰구간 안에서 불변이면 'proxy가 최적을 왜곡한다'는 전제는 무효화된다.

**가정**
- 두 논문의 compute-optimal 분석은 같은 6ND FLOP 근사를 쓴다
- fit 범위의 작은 모델/긴 문맥 영역에서 attention share는 무시할 수준이 아니다

**미지**
- attention 포함 exact FLOPs로 compute-optimal fit을 재측정할 때 frontier 이동과 지수 변화의 크기

**근거**
- `papers/kaplan2020` (conf 0.85) — training compute를 C ≈ 6·N·D로 추정했고 token당 비용을 문맥 길이와 무관하게 취급했다.
- `papers/hoffmann2022` (conf 0.80) — compute-optimal 분석(Approach 1-3) 역시 FLOP 추정값 C ≈ 6·N·D를 기준으로 fitting했다.

**반론 3건** · dissent_portfolio 등재
- [`evidence`/`wound`] Kaplan2020과 Hoffmann2022에서 사용된 표준 context window(1024~2048 토큰) 및 히든 차원 d_model 영역에서는 attention 연산 비중이 전체 6ND의 1~3% 미만에 불과함을 수식적으로 증명할 수 있다.
- [`premise`/`wound`] 두 논문의 fitting 범위 내 모델들에서 attention share가 무시할 수 없을 정도로 크다는 전제는, 8k 이상의 ultra-long context가 아닌 2k 기준 벤치마크에서는 수치적으로 기각된다.
- [`execution`/`wound`] 두 논문에 공개된 training run config에는 정확한 attention 구현체(FlashAttention vs 표준)나 커널 최적화 세부사항이 생략되어 있어, 공개 표만으로 완벽한 exact FLOPs를 역산하는 데 한계가 있다.

---

## Q-20260820-0003 · google(LWAR2) · OP-MISSVAR · cause

> 기존 scaling laws가 간과한 '토큰 중복도 및 데이터 시퀀스 다양성'을 공변량으로 도입할 때, 다중 epoch 반복 훈련 시 관측되는 scaling law 붕괴 지점이 데이터 다양성 한계에 의해 결정되는가?

**왜 중요한가** — objective=consensus_falsify

**최소 검정** — 변수 `sequence_diversity_index` · 비교 `1_epoch_unique vs 4_epoch_repeated at matched FLOPs` · **기각 조건 `loss_deviation_under_repeated_tokens == 0`**
**실행 계획** — `data` · multi_epoch_subsampled_token_corpora · metric `relative_loss_penalty_per_epoch` · 기준 `loss_penalty_exceeds_threshold_delta`

**반증 조건** — 토큰 중복도와 시퀀스 다양성을 극단적으로 변경해도 multi-epoch 학습의 loss 감소 곡선이 고유 토큰 1-epoch 곡선과 오차범위 내에서 동일하면 가설 기각

**가정**
- 데이터 반복 재사용 시 유효 토큰 수는 고유 토큰 수보다 작아짐
- 시퀀스 다양성 지수가 scaling frontier의 굴절점을 예측할 수 있음

**미지**
- 반복 훈련 시 compute-optimal frontier가 급격히 하향되는 변곡점을 결정하는 핵심 공변량 규명

**근거**
- `papers/hoffmann2022` (conf 0.88) — Hoffmann et al.은 compute-optimal 달성을 위해 막대한 고유 토큰 수가 필요함을 보여주어 데이터 고갈 문제를 시사함
- `papers/kaplan2020` (conf 0.82) — Kaplan et al.은 데이터 크기 D의 제약 하에서 반복 학습이 미치는 효과를 단일 power law 내에서 세부 분해하지 않음

**반론 5건** · dissent_portfolio 등재
- [`evidence`/`wound`] The citations motivate data quantity effects but do not directly measure sequence diversity or a multi-epoch collapse threshold.
- [`logic`/`wound`] A correlation between diversity and loss deviation would not establish that diversity determines the breakpoint.
- [`premise`/`wound`] It treats effective token capacity as a scalar reduction of raw token count.
- [`alternative`/`wound`] Memorization onset or optimizer overfitting could explain the observed multi-epoch loss penalty without a diversity-limited frontier.
- [`execution`/`wound`] The sequence-diversity index and zero-deviation rejection rule are not operationally calibrated.

---

## Q-20260820-0006 · openai(LWAR1) · OP-BOUND · scenario

> At what lifetime inference demand does a training-compute-optimal model cease to minimize total lifecycle compute and energy?

**왜 중요한가** — High-volume deployment can reverse a training-only recommendation, changing which scaling choice is economically and environmentally important.

**최소 검정** — 변수 `cumulative inference requests after training` · 비교 `equal-quality candidate models chosen from alternative parameter-data allocations` · **기각 조건 `total lifecycle compute preserves the same model ranking across the full deployment range`**
**실행 계획** — `simulation` · measured training runs combined with hardware-specific inference cost curves · metric `lifecycle joules and accelerator-seconds at equal task quality` · 기준 `identify the first demand interval where the training-only winner loses both lifecycle metrics`

**반증 조건** — No lifecycle boundary exists if the training-compute-optimal candidate also minimizes inference-adjusted cost for every feasible request volume.

**가정**
- Inference cost can be measured consistently across candidate model sizes.
- Candidate models meet the same task-quality threshold.

**미지**
- The deployment-volume threshold at which inference dominates the training allocation advantage.

**근거**
- `papers/kaplan2020` (conf 0.76) — The reported compute-efficient frontier is derived from training loss as a function of model, data, and training compute.
- `papers/hoffmann2022` (conf 0.80) — The reported optimum reallocates a fixed training-compute budget between parameters and training tokens.

**반론 3건** · dissent_portfolio 등재
- [`evidence`/`wound`] 제시된 근거 문헌(Kaplan2020, Hoffmann2022)은 훈련 손실 중심의 scaling 분석만을 다루고 있으며, 추론 시점의 양자화, KV 캐시 압축, 배치 처리 오버헤드 등 실제 하드웨어 추론 에너지에 관한 직접적 실증 데이터를 포함하지 않는다.
- [`premise`/`wound`] 후보 모델들이 동일한 태스크 퀄리티 임계치를 충족한다는 전제는, 벤치마크별 능력 발현 특성이 모델 크기에 따라 달라지므로 일반화하기 어렵다.
- [`execution`/`wound`] 하드웨어 아키텍처 세대 전환 및 메모리 대역폭 차이에 따라 추론 비용 곡선의 기울기가 급변하므로, 시뮬레이션 결과의 재현성이 하드웨어 특성에 과도하게 종속된다.

---

## Q-20260820-0004 · openai(LWAR1) · OP-CONTRA · phenomenon

> Under what quality-adjusted token distribution do parameter-favoring and balanced parameter-data compute prescriptions make measurably conflicting predictions, and where are they jointly consistent?

**왜 중요한가** — A quality-aware compatibility boundary would distinguish genuine disagreement between scaling prescriptions from differences caused by token accounting.

**최소 검정** — 변수 `effective information per token` · 비교 `matched-compute runs across controlled data-quality mixtures` · **기각 조건 `both prescriptions select statistically indistinguishable parameter-data allocations throughout the tested range`**
**실행 계획** — `experiment` · deduplicated corpora mixed with calibrated low-information replicas · metric `held-out loss per quality-adjusted token` · 기준 `detect a reproducible allocation crossover with confidence intervals excluding zero`

**반증 조건** — The question is vacated if quality-adjusted token accounting leaves both prescriptions observationally equivalent across all tested compute budgets.

**가정**
- Reported token counts can be mapped to an effective-information scale.
- Training loss remains comparable across controlled quality mixtures.

**미지**
- The quality distribution at which the two prescriptions cease to recommend overlapping model and data allocations.

**근거**
- `papers/kaplan2020` (conf 0.78) — Parameter count, dataset size, and training compute exhibit separable empirical scaling relationships under the studied training setup.
- `papers/hoffmann2022` (conf 0.82) — Compute-optimal training in the studied regime increases model size and training tokens together rather than allocating most additional compute to parameters.

**반론 3건** · dissent_portfolio 등재
- [`evidence`/`wound`] Kaplan2020과 Hoffmann2022는 사용한 데이터셋(WebText2 vs MassiveText)뿐만 아니라 LR schedule(cosine vs warmup-decay)과 토큰당 유효 batch 크기 설정이 달라, 단순 품질 보정만으로는 두 연구의 스케일링 지수 차이를 온전히 분리해내기 어렵다.
- [`premise`/`wound`] 모든 토큰을 단일한 '유효 정보량(effective-information scale)' 스칼라 값으로 일대일 매핑할 수 있다는 전제는 언어의 문맥 의존성과 다의성을 과도하게 단순화한 가정이다.
- [`execution`/`wound`] 보정된 저품질 복제 데이터셋(calibrated low-information replicas)을 합성하여 통제 실험을 수행할 때, 합성 과정 자체가 인위적 artifact를 유발하여 실제 웹 데이터 분포를 대변하지 못할 위험이 있다.

---

## Q-20260820-0002 · google(LWAR2) · OP-XDOM · cause

> 비평형 열역학의 유효 온도 및 엔트로피 생성률 개념을 LLM 훈련 손실 궤적에 매핑할 때, Kaplan과 Hoffmann 간 최적 배분 지수 차이는 훈련 데이터셋의 엔트로피 밀도 불균일성에 의해 유도되는 비가역 손실 성분으로 정량 설명되는가?

**왜 중요한가** — objective=consensus_falsify

**최소 검정** — 변수 `irreversible_entropy_production_rate` · 비교 `controlled_entropy_corpus vs standard_web_corpus` · **기각 조건 `entropy_production_correlation < 0.10`**
**실행 계획** — `simulation` · information_density_controlled_token_stream · metric `effective_loss_thermodynamic_entropy_ratio` · 기준 `r_squared_greater_than_0_80`

**반증 조건** — 엔트로피 밀도를 통제한 단일 코퍼스에서도 데이터셋 다양성 변조와 무관하게 Kaplan-Hoffmann 지수 차이가 불변으로 유지되면 가설 기각

**가정**
- 손실 감소 과정을 매크로 상태 전이로 정량화 가능
- 토큰 시퀀스의 정보 엔트로피 밀도가 훈련 dynamics의 유효 온도를 결정함

**미지**
- 데이터 품질/정보밀도 차이가 scaling exponent의 불일치를 일으키는 근본 물리적 메커니즘인지 여부

**근거**
- `papers/kaplan2020` (conf 0.85) — Kaplan 모델은 WebText2 등 특정 데이터셋 상에서 토큰 수보다 파라미터 수에 더 민감한 거듭제곱 법칙을 도출함
- `papers/hoffmann2022` (conf 0.90) — Hoffmann 모델은 MassiveText 상에서 N과 D의 균등 분할이 최적임을 입증함

**반론 5건** · dissent_portfolio 등재
- [`evidence`/`wound`] 인용된 두 claim은 각 데이터셋에서의 조건부 fitting 결과를 보고할 뿐, 질문이 설명하려는 엔트로피 밀도 불균일성이나 비가역 손실 성분을 측정한 증거가 아니다. 증거와 질문의 핵심 개념 사이에 측정 연결고리가 없다.
- [`logic`/`wound`] 유효 온도와 엔트로피 생성률을 훈련 손실 궤적에 매핑하는 대응 규칙이 정의되지 않은 채 '정량 설명되는가'를 묻고 있다. order parameter가 없으면 설명 성공/실패를 판정할 명제 자체가 성립하지 않는다.
- [`premise`/`wound`] '토큰 시퀀스의 정보 엔트로피 밀도가 훈련 dynamics의 유효 온도를 결정한다'는 전제는 독립 근거 없이 채택되었고, 정의적 편의가 아니라 경험적 주장인지 구분되지 않는다.
- [`alternative`/`wound`] 지수 차이의 더 단순한 대안 설명으로 optimizer/LR schedule/tokenizer 차이가 이미 알려져 있다. thermodynamic 매핑 없이도 갭의 상당 부분이 설명되므로, 이 질문은 대안과의 설명력 비교를 통과해야 한다.
- [`execution`/`wound`] action_plan의 metric(effective_loss_thermodynamic_entropy_ratio)과 variable(irreversible_entropy_production_rate)은 매핑이 미정의인 상태에서 구현 불가능한 이름이다. 실행 설계가 미해결 개념 정의를 전제한다.

---

## Q-20260820-0001 · google(LWAR2) · OP-SCALE · phenomenon

> 동일 compute 예산 하에서 토큰 수(D) 대비 파라미터 수(N)를 극한으로 스케일(N >> D)할 때, loss power-law의 지수가 포화되는 병목은 모델 파라미터 용량 한계인가 아니면 gradient noise scale에 따른 유효 배치사이즈 한계인가?

**왜 중요한가** — objective=consensus_falsify

**최소 검정** — 변수 `gradient_noise_scale_adjusted_loss_gap` · 비교 `fixed_batch vs adaptive_noise_batch at extreme N/D` · **기각 조건 `p_value > 0.05 on difference in loss exponent`**
**실행 계획** — `experiment` · synthetic scaling benchmark across 1e18 to 1e22 FLOPs · metric `power_law_scaling_exponent_alpha` · 기준 `delta_alpha_statistically_significant`

**반증 조건** — 극단적 N/D 스케일 regime에서도 gradient noise scale 조정 유무와 무관하게 loss 지수와 수렴 궤적이 단일 파라미터 scaling law 곡선을 완벽히 추종하면 가설 기각

**가정**
- Kaplan 2020 및 Hoffmann 2022의 scaling relation은 특정 compute regime에서 성립함
- 극단적 N/D 비율에서 최적화 역학이 변경됨

**미지**
- 극단적 스케일에서 관측되는 loss 정체가 모델 파라미터 용량 부족인지 유효 배치사이즈 및 gradient 노이즈 병목인지 여부

**근거**
- `papers/kaplan2020` (conf 0.80) — Kaplan et al.은 큰 모델일수록 sample efficiency가 높으며 compute 예산 증가 시 N이 D보다 빠르게 증가해야 한다고 제안함
- `papers/hoffmann2022` (conf 0.90) — Hoffmann et al.은 compute-optimal frontier에서 N과 D가 1:1에 가깝게 비례 스케일되어야 함을 보임

**반론 5건** · dissent_portfolio 등재
- [`evidence`/`wound`] The cited scaling papers do not directly establish gradient-noise scale as the competing bottleneck at extreme parameter-to-token ratios.
- [`logic`/`wound`] The question frames parameter capacity and effective batch size as an exhaustive binary.
- [`premise`/`wound`] It assumes a well-defined power-law exponent remains identifiable after moving far outside the fitted scaling regime.
- [`alternative`/`wound`] A data-entropy bottleneck offers a third explanation for the same loss flattening.
- [`execution`/`wound`] A single p-value on fitted exponents is insufficient across four orders of magnitude of compute.

---
