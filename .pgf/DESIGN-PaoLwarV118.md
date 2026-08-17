# PAO-LWAR v1.18 개선 설계

**Status** P1–P6 done — `ProbeScriptUpgrade` 만 designing · **Target** `.agents/skills/pao-lwar` v1.17 (runtime protocol 1.4.2)
**Source** `_workspace/lwar-skill-review/integrated-review.md` (8개 런타임 통합 리뷰, D1–D37)
**추가 근거** 2026-08-16 OA 세션 버스 실증 (R1, R2 — §2)
**계약 검증** 2026-08-16 `task-pao-ack-20260816` — exit-notify 계약 end-to-end 1회 통과 (§10)
**Notation** PG v1.4 (Gantree + PPR). 이 문서가 PPR 권위다.

---

## 1. 문제 정의

v1.17의 결함은 **프로토콜 코어가 아니라 세 층**에 있다. 통합 리뷰에서 코드를 실제 대조한 3인(claude·qwen·glm) 모두 신원·펜스·토큰·전환 그래프·exit code가 코드와 일치한다고 판정했고, 모든 실행 리뷰에서 `doctor --role lwar`가 healthy였다.

| 층 | 증상 | 근거 |
|---|---|---|
| **문서 잔재** | v1.17에서 공식 경로가 `--background` → exit-notify로 이동했으나 구 의미론이 3곳에 잔존 | D1·D2·D3 (파일·행 검증됨) |
| **호스트 모델 괴리** | 스킬은 Codex/Kimi 2종을 전제하는데 실측 8종 중 live-notify가 0건, foreground 10분 상한이 다수 | D5·D6·D7·D11·D12 |
| **슬롯 수명주기 공백** | 채택되지 않은 등록과 미수령 control이 슬롯을 영구 점유하고, OA에 회수 명령이 없다 | **R1·R2 (오늘 실증)** |

앞 두 층은 문서 패치로 닫힌다. 세 번째는 **런타임 변경**이 필요하며, 이번 설계에서 새로 추가된 축이다.

---

## 2. 실증된 런타임 결함 (오늘 관측, 리뷰 원문 밖)

### R1 — 채택되지 않은 슬롯을 회수할 수 없다

`reconcile`이 등록을 승인한 뒤 LWAR가 identity를 채택하지 않으면 슬롯은 `runtime_status=registered_not_started`로 남는다. 이 상태에서:

```text
recover --reap-startup  → heartbeat_identity_mismatch  (거부)
recover --retire-stale  → heartbeat_identity_mismatch  (거부)
```

`reap_startup`은 **matching identity + `status=starting` 하트비트**를 요구하고(`registry.py:315-334`), `retire_stale`은 **matching identity + 관측된 `last_seen` 일치**를 요구한다(`registry.py:167-204`). 채택 전 슬롯에는 현행 세대 하트비트가 아예 없으므로 두 경로 모두 구조적으로 도달 불가다. 레지스트리 손편집은 금지 항목이다.

**실측**: LWAR2(`lwar-instance-dc6f2bd6…`, gen 2)에 두 명령을 모두 시도 → 양쪽 `heartbeat_identity_mismatch`, `registry_version` 14 불변(무변이 실패).

이것은 통합 리뷰 D9·D10의 귀결이다. 리뷰 세션이 남긴 등록이 실제 슬롯을 점유했고, OA에게 회수 수단이 없다.

### R2 — 미수령 control이 stale 슬롯 은퇴를 영구 차단한다

`retire_stale`은 `incoming/claimed/leases/outgoing/control/control_claimed` 전 채널이 비어야 한다. 그러나 죽은 watcher 앞으로 발행된 control은 **아무도 claim하지 않으므로 영원히 남는다**. `prune`의 `PRUNE_CATEGORIES`는 `archive/*`, `failed`, `quarantine`, `cancelled`뿐이고(`transport.py:32-39`) 대기 중 `control/`을 다루지 않는다.

**실측**: LWAR1은 `stale_confirmed=true`인데도 `collect --archive`로 `outgoing`을 비운 뒤에도 미수령 `shutdown` control 1건 때문에 `active_mailbox_work`로 거부됐다.

> 자기 참조적 함정: watcher를 멈추려고 보낸 `shutdown`이 그 watcher가 죽었기 때문에 슬롯 회수를 막는다.

---

## 3. 설계 제약

```python
CONSTRAINTS = {
    "runtime_duplication": "pao-lwar/pao_runtime/ 와 pao-oa/pao_runtime/ 는 대부분 byte-identical 사본",
    "known_divergence":    "lwar_cli.py / adp_watch.py / pao_cli.py 는 초기 커밋부터 이미 상이 — 역할별 차이",
    "parity_gate_scope":   "변경한 모듈만 두 사본 동일하면 통과. 기존 상이 3종을 통일하려 들지 말 것",
    "version_lockstep":    "runtime_version 변경은 두 번들 동시 반영 필수",
    "fail_closed_gate":    "register 는 runtime_version 을 스탬프하고 OA 가 불일치를 fail-closed 거부",
    "no_hand_edit":        "registry / mailbox / lease 손편집 금지 (양 스킬 공통 금지사항)",
    "doc_only_default":    "P1·P3·P5·P6 은 문서만 — 런타임 무변경, 버전 무영향",
    "runtime_change":      "P2 일부 + P4 전체 — 프로토콜 변경 시 1.4.2 → 1.5.0 및 버스 호환 판단 필요",
}
```

`registry.py` md5 대조로 두 사본의 동일성을 확인했다. **한쪽만 버전을 올리면 모든 신규 등록이 `runtime_version_mismatch`로 거부된다** — P4 실행 전 반드시 인지할 것.

---

## 4. POLICY

```python
POLICY = {
    "_version":        "2.6",
    "max_retry":       2,
    "on_blocked":      "halt",
    "completion":      "all_done_or_blocked",
    "design_authority": ".pgf/DESIGN-PaoLwarV118.md",
    "evidence":        "_workspace/lwar-skill-review/integrated-review.md",
    "doc_gate":        "번들 전체 grep 으로 모순 문장 0건",
    "runtime_gate":    "두 사본 md5 동일 + pytest tests/pao 통과",
    "no_version_bump_without": "pao-lwar 와 pao-oa 동시 반영",
}
```

`halt`: 런타임 변경 노드(P4)가 막히면 문서 노드로 우회하지 않고 정지하고 보고한다.

---

## 5. Execution Tree

```text
PaoLwarV118 // pao-lwar v1.17 → v1.18 @v:1.0 (done)
    P1_CanonicalPath // 공식 경로 단일화 — S0 전부의 공통 뿌리 (done) #D1 #D2 #D3
        NotifyStyleTable // notify_style 별 canonical 명령 단일 표 신설 (done)
            # Target: SKILL.md §2 (새 절 "Canonical commands by notify_style")
            # Task: 등록·채택·watcher·재시작 4단계 × exit-notify/live-notify 2열 표
            # criteria: 같은 이벤트에 두 개의 명령을 지시하는 문장이 번들에 0건
        AdpLoopSplit // adp-loop.md Core loop 을 스타일별로 분리 (done) @dep:NotifyStyleTable
            # Target: references/adp-loop.md:57,86,96 + exit code 표
            # Task: 기존 의사코드를 "live-notify / --background 전용" 으로 라벨링,
            #       exit-notify 루프 의사코드 병렬 추가, exit code 표에 적용스타일 컬럼
            # criteria: kimi-cli-adapter.md 의 exit 0/20 표기와 행 단위 일치
        RegisterReorder // register.md 첫 코드블록을 --resident 로 승격 (done) @dep:NotifyStyleTable
            # Target: references/register.md:64 ↔ :80 순서 교체
            # criteria: 파일을 위에서 아래로 실행해도 공식 경로에 도달
        ReadmeFix // scripts/README.md 기본값 문장 교체 (done) @dep:NotifyStyleTable
            # Target: scripts/README.md:23-24, :28-29
            # criteria: "default … background watcher" 문자열 0건
        PrecedenceRule // 권위 순서 선언 (done)
            # Rule: adapter 제약 > probe 결과 > 일반 기본값
            # Target: SKILL.md §2 "Canonical commands by notify_style" 머리말
            # criteria: codex P0 (§0.5 ↔ §2 라우팅표 상충) 이 규칙 적용으로 결정 가능
        RuleStyleGeneralize // Rule 3·9 를 호스트명이 아닌 notify_style 로 재서술 (done)
            # Target: SKILL.md:159 (Rule 9 "Do not kill the background process"), Rule 3
            # criteria: exit-notify 수행자가 죽은 프로세스에 Rule 9 를 적용하지 않음
    P2_HostContract // 호스트 능력 계약 — 실측 8종 기반 (done) #D5 #D6 #D7 #D12 #D14
        # ProbeScriptUpgrade 만 designing 으로 남김 — 1c 의 fail-closed 가 급성 위험을 제거
        HostMatrix // 실측 매트릭스를 host-adapter.md 정본으로 편입 (done) #D11
            # Source: integrated-review.md §2 (8 런타임 실측)
            # Task: 벤더별 문서 5개 신설 대신 표 1개 + 3~5행 스텁
            # criteria: 신규 호스트가 자기 행을 추가하는 것만으로 어댑터 문서 완성
        ProbeSplit // bg_timeout_50m 을 3 값으로 분해 (done)
            # 아래 def AI_classify_host_timeout 참조
        BlockingCapRule // 축소 슬라이스 인가 규칙 (done) @dep:ProbeSplit
            # 아래 def resolve_max_runtime 참조
        LiveNotifyDefinition // "폴링 없이 깨우는 경우만 live-notify" (done)
            # Target: references/host-notify-probe.md §2
            # criteria: Claude Code(TaskOutput 폴링), Grok(snapshot) 둘 다 exit-notify 로 판정
        HostExitCaveat // tool wrapper exit != process exit (done)
            # 분기 키는 stdout JSON 의 event/status. host-reported exit 는 보조
            # criteria: grok 실측(RC 2 를 host 가 1 로 보고) 사례가 문서로 설명됨
        ProbeScriptUpgrade // host_notify_probe.py 에 타임스탬프 출력 (designing)
            # Target: scripts/host_notify_probe.py (양 번들)
            # 판정 근거를 세션 기억이 아닌 출력으로 남긴다. deepseek F4
    P3_Portability // standalone 계약 회복 (done) #D4 #D8 #D13 #D17
        IdentityPathRedaction // 하드코딩 identity 절대경로 제거 (done)
            # Target: references/codex-cli-adapter.md:27
            # Replace: <BUS_ROOT>/var/identities/<instance_id>.json
            # criteria: 번들 전체 grep 에서 실제 instance_id 문자열 0건
        TrustedHandoffRule // 레퍼런스 경로 != trusted handoff 명문화 (done) @dep:IdentityPathRedaction
            # Target: SKILL.md §0.5
            # criteria: 신규 세션이 문서에 적힌 경로를 채택하지 않음이 규칙으로 강제됨
        IfOverlayExtraction // kimi-cli-adapter.md 의 IF 결합 분리 (done)
            # Target: references/kimi-cli-adapter.md:112-114
            # Task: if_lwar.py / visibility jail / question_id 항목을 if-lwar 스킬로 이동
            # criteria: standalone 번들에 if-* 참조 0건
        RequiredReadingSet // start 필수 독서 목록 축소 (done) @dep:IdentityPathRedaction
            # 필수: collaboration-principles, host-notify-probe, register,
            #       adp-loop, execute-complete, lifecycle
            # 조건부: host-adapter + 벤더 어댑터 (adapter_id 일치 시에만)
            # criteria: §0 "모든 레퍼런스" 와 §1 Rule 1 "행동 직전" 의 충돌 해소
        ShellQuotingNote // 따옴표 미보존 셸 경고 (done)
            # 근거: deepseek 실측 실패 (--runtime-name "DeepSeek TUI" 분해)
            # criteria: 공백 포함 인자에 대한 대체 표기가 문서에 존재
    P4_SlotLifecycleGap // 슬롯 수명주기 — 런타임 변경 (done) #R1 #R2 #D9 #D10
        UnadoptedSlotReclaim // 채택 전 슬롯 회수 경로 (done) — recover --reclaim-unadopted
            # 아래 def reclaim_unadopted_slot 참조
        ControlExpiry // 미수령 control 의 만료·회수 (done) — recover --expire-controls
            # 아래 def expire_pending_control 참조
        RegistrationPendingBound // registration_pending 재시작 상한 (done) — Rule 13
            # Target: pao-lwar SKILL.md Rule 13 + references/register.md
            # Task: 연속 N회 또는 wall-clock 예산 초과 시 재시작 중단 → request_id 와 함께 보고
            # criteria: OA 부재 버스에서 LWAR 세션이 유한 시간에 정지 보고로 수렴
        RegisterCancel // 승인 전 등록 철회 (done, D1=B) @dep:RegistrationPendingBound
            # Option A: lwar.py register-cancel --request-id (LWAR 자기 정리)
            # Option B: 문서만 — "고아 pending 은 OA 만 정리 가능" 명시 + OA 명령 추가
            # 미결: §7 D1
        SessionPurposeField // 세션 의도 선언 (done, D2=B) — §0.5 규범
            # Task: register 에 --purpose review|smoke|production 또는
            #       "실작업 의도 없는 세션은 register 금지" 규범
            # 근거: 오늘 리뷰 세션 등록 2건이 실제 슬롯 점유 (D10 실증)
            # 미결: §7 D2
    P5_ResultContract // 결과·오류 계약 (done) #D15 #D16 #D19 #D22 #D26 #D35
        ExitCodeDictionary // exit code 사전 통합 (done) — lifecycle.md, 실측 대조
            # Task: status 0/2/3/4 + begin 0/4 + complete 0/1 + adp 10/20/30/40
            #       + registration_rejected 3 + status exit 1(파일 부재) 을 한 표로
            # criteria: 문서에 없는 exit code 가 CLI 표면에 0건
        CompleteIdempotency // complete 멱등성·재시도 계약 (done) — execute-complete.md
            # Task: "exactly one terminal result" 를 논리 결과 1개로 정의,
            #       stdout 유실/timeout 시 status 조회 → 동일 execution_token 재시도 절차
            # criteria: 제출 후 timeout 시나리오에서 결정 절차가 유일하게 결정됨
        PermissionGateStatus // 권한 거부 시 blocked 제출 (done)
            # Target: references/execute-complete.md 상태 표 1행 추가
            # criteria: 무인 루프에서 lease 만료 방치 대신 terminal 제출로 수렴
        CancelLimitNote // exit-notify 의 cancel 한계 명시 (done)  # AdpLoopSplit 과 함께 조기 완료
            # "cancel 은 complete 후 watcher 재시작 시 처리. 중단 지연 상한 = 태스크 실행 시간"
        NextActionSpec // next_action 허용값 명세 (done) — validate | none, OA 미소비
            # 현재 스키마는 non-empty string, 예시는 "validate" 하나뿐
            # OA 소비 방식 미정 — 값 집합 확정 필요
    P6_Hygiene // 위생 묶음 (done) #D18 #D20~D37
        ArgumentHintFix // argument-hint 에 adp|adp-stop|adp-wait 추가, start 표기 정정 (done)
        DanglingRefFix // (§1.3) → SKILL.md §1 Rule 6 (done)
        LegacyIdentityWording // "Legacy identities" → 현행 정본 위치로 재서술 (done)
        ConformanceNote // conformance/ 용도 1문단 + README (done)
            # 현재 SKILL.md·references 전체에 "conformance" 문자열 0건 (검증됨)
        MailboxLayoutSync // executions/ · invocation.json · watcher.pid.json 반영 (done)
        LifecycleGraphFix // 실제 전환 그래프 표 (done)
        MiscDocPack // 나머지 소항목 일괄 (done)
            # PAO_LWAR_IDENTITY 폴백, schemas 목차, watcher stdout 이벤트 예시,
            # 상태 전이도, 보고 템플릿, shebang python3, behavior_contract 설명,
            # skill/protocol 버전 관계, register [number] 의미, blind-safe 강조,
            # identity_leaks 오검출 주의, monitor 류 idle-kill 금지, result_draft_path
```

---

## 6. PPR

### `AI_classify_host_timeout` — ProbeSplit

```python
def AI_classify_host_timeout(host: HostFacts) -> TimeoutVerdict:
    """bg_timeout_50m 단일 판정을 두 독립 검사로 분해한다.

    현행 규칙("timeout 옵션을 50분 이상으로 설정 가능하면 pass")은 판정 불능이다.
    동일한 '옵션 없음 + background 무제한' 형태에 대해 리뷰어 판정이
    pass / fail / 판정불가 로 3분기했다 (integrated-review D6).
    """
    # 검사 1 — 옵션 수용
    if host.max_timeout_option_s is None:
        option = "no_option"          # 옵션 자체가 없음
    elif host.max_timeout_option_s >= 3000:
        option = "accepted"
    else:
        option = "capped"             # 제출 자체가 불가 → 확정 fail 요인

    # 검사 2 — kill 시 stdout 전달 (이것이 exit-notify 재시작 루프의 전제)
    delivery = host.stdout_delivered_on_kill   # True | False | "unknown"

    # 합성 — 불확실은 축소 슬라이스로 fail-closed
    if option == "accepted" and delivery is True:
        return TimeoutVerdict(pass_=True, slice_s=3000)
    if option == "no_option" and host.background_unbounded and host.stdout_on_exit:
        # Qwen Code / Antigravity / Claude Code background 형태
        return TimeoutVerdict(pass_=True, slice_s=3000, note="unbounded_background")
    return TimeoutVerdict(pass_=False, slice_s=None, note="use_reduced_slice")

    # acceptance_criteria:
    #   - integrated-review §2 의 8개 런타임을 입력하면 각 리뷰어의 근거와
    #     모순되지 않는 단일 판정이 나온다
    #   - "unknown" delivery 는 절대 pass 로 떨어지지 않는다
```

### `resolve_max_runtime` — BlockingCapRule

```python
def resolve_max_runtime(host_blocking_cap_s: int | None, margin_s: int = 60) -> int:
    """호스트 blocking 상한에 맞춰 슬라이스를 축소한다.

    CLI 는 이미 --max-runtime-s 를 지원한다 (adp_exit_notify.py, lwar.py adp).
    문서만의 공백이므로 코드 변경 없이 규칙 추가로 닫힌다.
    """
    ADP_MAX = 3000
    if host_blocking_cap_s is None:          # 상한 없음
        return ADP_MAX
    return min(ADP_MAX, max(60, host_blocking_cap_s - margin_s))

    # 계약 불변:
    #   - idle_timeout(exit 10) 재시작 주기만 짧아진다. 프로토콜은 변하지 않는다
    #   - 호스트 강제 kill 이 아니라 정상 idle_timeout 으로 종료되게 하는 것이 목적
    # acceptance_criteria:
    #   - foreground 600s 호스트(Claude Code / DeepSeek / Qwen Code)가
    #     공식 경로만으로 무한 운용 가능 → 540 반환
    #   - host-adapter.md 의 timeout recovery 를 상시 경로로 쓰지 않게 된다
```

### `reclaim_unadopted_slot` — UnadoptedSlotReclaim (R1)

```python
def reclaim_unadopted_slot(lwar_id: str, instance_id: str, generation: int,
                           unadopted_after_s: float, reason: str) -> Outcome:
    """승인됐으나 identity 가 채택되지 않은 슬롯을 펜스 안에서 회수한다.

    기존 두 경로는 모두 '현행 세대 하트비트'를 요구하므로 채택 전 슬롯에
    구조적으로 도달하지 못한다 (R1 실측).
    """
    with registry_lock():
        slot = load_slot(lwar_id)
        # 펜스 — 기존 두 명령과 동일한 엄격도
        require(slot.instance_id == instance_id and slot.generation == generation)
        require(slot.runtime_status == "registered_not_started")
        require(current_generation_heartbeat(lwar_id) is None)   # 채택 흔적 없음
        require(age_since(slot.approved_at) > unadopted_after_s)
        require(active_mailbox_work(lwar_id) == {})
        require(reason.strip() != "")

        commit_tombstone(lwar_id, generation, mode="unadopted_reap", reason=reason)
        remove_slot(lwar_id)
        audit("unadopted_slot_reclaimed", key=f"{lwar_id}:{instance_id}:{generation}")
    return Outcome(accepted=True)

    # 실패 분기 — 전부 fail-closed, 무변이
    #   identity_mismatch / heartbeat_present(채택됨) / not_unadopted /
    #   active_mailbox_work / reason_empty
    # acceptance_criteria:
    #   - 동일 명령 재실행이 멱등 (already_reclaimed)
    #   - 채택 완료된 슬롯에는 절대 적용되지 않는다
    #   - tombstone 이 generation 을 보존해 재등록 시 generation+1
```

### `expire_pending_control` — ControlExpiry (R2)

```python
def expire_pending_control(lwar_id: str, older_than_s: float, reason: str) -> Outcome:
    """죽은 watcher 앞으로 남은 미수령 control 을 만료 처리한다.

    prune 의 PRUNE_CATEGORIES 는 대기 중 control/ 을 다루지 않으므로
    (transport.py:32-39) 미수령 control 이 retire_stale 을 영구 차단한다 (R2 실측).
    """
    with registry_lock():
        for control in pending_controls(lwar_id):
            require(age_of(control) > older_than_s)
            # 살아있는 watcher 를 가진 슬롯은 건드리지 않는다
            require(runtime_status(lwar_id) in {"stale", "registered_not_started"})
            move_to(control, f"mailbox/{lwar_id}/archive/control/",
                    annotate={"expired": True, "expiry_reason": reason})
            audit("control_expired", key=control.control_id)
    return Outcome(expired=count)

    # 설계 선택 — 삭제가 아니라 archive/control/ 로 이동 (증거 보존)
    # acceptance_criteria:
    #   - runtime_status=active 슬롯의 control 은 절대 만료되지 않는다
    #   - 만료 후 retire_stale 이 같은 슬롯에서 성공한다
    #   - control_claimed(수령 후 미확인)는 대상이 아니다 — 별개 복구 경로
```

### 실행 파이프라인

```python
P1_docs -> AI_verify_no_contradiction(bundle) -> gate_1

[parallel]
P2 = AI_apply(host_contract, evidence=integrated_review_section_2)
P3 = AI_apply(portability_patches)
[/parallel]
-> AI_verify_standalone(bundle)   # if-* 참조 0, 하드코딩 경로 0
-> gate_2

P4_runtime -> AI_mirror(pao_lwar_runtime, pao_oa_runtime)
           -> AI_verify(md5_identical and pytest_pao_pass)
           -> gate_3   # 실패 시 halt (POLICY.on_blocked)

[P5, P6] -> AI_apply(doc_patches) -> gate_4
```

파이프라인 단계가 실패하면 정지하고 마지막 성공 출력을 유지한다(PG 기본 규칙). P4의 gate_3 실패는 `halt` — 문서 노드로 우회하지 않는다.

---

## 7. 결정 (2026-08-16 확정, 정욱님 승인)

| # | 결정 | 채택 | 근거 |
|---|---|---|---|
| **D1** | `RegisterCancel` 구현 위치 | **(B) OA 명령 하나로 통합** | LWAR 측 철회를 만들어도 `reconcile` 승인과의 경합이 남아 결국 R1 회수 경로가 또 필요하다. `recover --reclaim-unadopted` 범위를 승인 전 고아 요청까지 넓힌다. LWAR CLI 표면은 늘리지 않는다(D13) |
| **D2** | `SessionPurposeField` 강제성 | **(B) 문서 규범만** | `--purpose`는 정직성에 의존한다 — 스스로 붙일 판단력이 있는 세션은 애초에 register를 안 한다(glm·qwen 실증). 실효 방어는 R1의 `unadopted_after_s`(24h 제안) 자동 후보화가 담당 |
| **D3** | 버전 정책 | **(A) 1.4.2 유지, 명령만 추가** | R1·R2 해결에 스키마 변경이 불필요하다. wire format 불변이므로 살아있는 LWAR3 무영향. 한쪽 번들만 반영되면 전 등록이 `runtime_version_mismatch`로 죽는 실패 모드만 커진다. tombstone `retirement_mode` 확장은 **additive-only** |
| **D4** | 막힌 LWAR1/LWAR2 | **(A) P4 구현 후 정식 회수. 급하지 않음** | 막힌 슬롯은 **기능적으로 무해**하다 — 신규는 LWAR4+로 등록되고 `send --auto`가 `stale`/`registered_not_started`를 자동 배제한다. (B) 새 버스는 audit·ledger 이력을 끊고 살아있는 LWAR3까지 죽인다 |
| **D5** | LWAR3 (active) | **유지. 죽이지 않음** | 살아있는 워커를 죽일 이유가 없다. HANDOFF §7-1 벤더 3-LWAR이 이미 1/3 채워졌다. 다음 단계는 PAO ack probe |

### 확정 실행 순서

| 순위 | 작업 | 상태 |
|---|---|---|
| 0 | `CLAUDE.md` 동기화 — 진입 라우팅이 구버전 강제 | **done** (2026-08-16) |
| 1 | **P1 + P3** (문서만, 위험 0) | **done** (2026-08-16) |
| 2 | **P2** 호스트 계약 — 다음 벤더 등록 **전**에 필요 | **done** (2026-08-16, `ProbeScriptUpgrade` 제외) |
| 3 | LWAR3 ack probe | **done** (2026-08-16) — `task-pao-ack-20260816` succeeded, semantic `accepted`, LWAR3가 `complete` 후 watcher 재기동해 `watching` 복귀 |
| 4 | **P4** 런타임 — 막힌 슬롯이 무해하므로 급하지 않음 | **done** (2026-08-16) — §11 |
| 5 | **P5** 결과·오류 계약 | **done** (2026-08-16) — §12 |
| 6 | **P6** 위생 + `v1.18` 확정 | **done** (2026-08-16) — §13 |

판단 근거: **지금의 실제 리스크는 "다음 벤더 세션이 잘못된 워처를 띄우는 것"이지 "슬롯 2개가 잠긴 것"이 아니다.** 문서 층을 먼저 닫고 런타임 변경은 검증 뒤에 한다.

### 순위 0 — 범위 밖이었던 항목

프로젝트 `CLAUDE.md`가 `adp_watch.py --background --report-every 86400` + 턴 종료를 강제하고 있었다(claude 2.6). 스킬 밖 파일이라 P1~P6 어디에도 없었으나, **진입 라우팅 문서가 구버전 행동을 강제하면 스킬 패치가 무효화된다.** 1줄 수정으로 exit-notify 기본 + 프로브 선행으로 교체했다.

---

## 8. 검증 (Acceptance)

| ID | 대상 | 판정 |
|---|---|---|
| V1 | P1 | 번들 grep: `default … background watcher` 0건, `--background` 를 첫 명령으로 제시하는 코드블록 0건 |
| V2 | P1 | adp-loop.md exit code 표와 kimi-cli-adapter.md 표가 행 단위 일치 |
| V3 | P2 | §2 매트릭스 8행 입력 → `AI_classify_host_timeout` 이 각 리뷰어 근거와 모순 없는 단일 판정 |
| V4 | P2 | foreground 600s 호스트가 `resolve_max_runtime` → 540, 공식 경로만으로 운용 가능 |
| V5 | P3 | 번들 전체에 실제 `lwar-instance-*` 문자열 0건, `if-*` 참조 0건 |
| V6 | P4 | `registered_not_started` 슬롯에 회수 명령 성공 + 멱등 재실행 `already_reclaimed` |
| V7 | P4 | 미수령 control 만료 후 동일 슬롯에서 `retire-stale` 성공 |
| V8 | P4 | `runtime_status=active` 슬롯에 P4 명령 전부 fail-closed |
| V9 | 전체 | `pao-lwar/pao_runtime` 와 `pao-oa/pao_runtime` md5 동일 |
| V10 | 전체 | `pytest tests/pao` 통과 |

---

## 9. 노드 ↔ 근거 매핑

| Phase | 노드 | 통합 리뷰 ID | 합의 | 검증 |
|---|---|---|---|---|
| P1 | AdpLoopSplit | D1 | 4/8 | adp-loop.md:57,86,96 |
| P1 | RegisterReorder | D2 | 4~5/8 | register.md:64 ↔ :80 |
| P1 | ReadmeFix | D3 | 4/8 | scripts/README.md:23-24,28-29 |
| P1 | PrecedenceRule | codex P0 | 2/8 | SKILL.md §0.5 ↔ §2 |
| P1 | RuleStyleGeneralize | D20 (Rule 3·9) | 1/8 | SKILL.md:159 |
| P2 | ProbeSplit | D6 | **6/8** | 리뷰어 판정 3분기 |
| P2 | BlockingCapRule | D5 | 4/8 | argparse 확인 (3인) |
| P2 | LiveNotifyDefinition | D7 | 3/8 | live-notify 실측 0/8 |
| P2 | HostMatrix | D11, D12 | 3+5/8 | §2 실측표 |
| P2 | HostExitCaveat | D14 | 2/8 | grok 실측 (RC 2 → host 1) |
| P3 | IdentityPathRedaction | D4 | **5/8** | codex-cli-adapter.md:27 |
| P3 | IfOverlayExtraction | D8 | 4/8 | kimi-cli-adapter.md:112-114 |
| P3 | RequiredReadingSet | D13 | 2/8 | §0 ↔ Rule 1 |
| P3 | ShellQuotingNote | D17 | 3/8 | deepseek 실행 실패 |
| P4 | UnadoptedSlotReclaim | **R1** + D9/D10 | 실증 | registry.py:315-334, 167-204 |
| P4 | ControlExpiry | **R2** | 실증 | transport.py:32-39 |
| P4 | RegistrationPendingBound | D9 | 3/8 | 고아 `.pending.json` 관측 |
| P4 | SessionPurposeField | D10 | 4/8 | LWAR2/LWAR3 슬롯 점유 |
| P5 | ExitCodeDictionary | D15, D26, D35 | 3/8 | |
| P5 | CompleteIdempotency | D15 | 3/8 | |
| P5 | PermissionGateStatus | D19 | 1/8 | |
| P5 | CancelLimitNote | D16 | 1/8 | Rule 5 구조 확인 |
| P6 | ConformanceNote | D18 | 2/8 | grep 0건 |
| P6 | 나머지 | D20~D37 | 1~3/8 | |

---

## 10. 계약 검증 기록 — `task-pao-ack-20260816`

P1·P2로 고친 exit-notify 계약이 실제 LWAR에서 작동하는지 확인한 첫 end-to-end 실행이다.
이전까지의 유일한 증거는 HANDOFF의 Grok 스모크 1건이었고, 그것도 3-LWAR/이종 벤더 증명이 아니라고 명시돼 있었다.

| 단계 | 관측 |
|---|---|
| `send --lwar-id LWAR3` | `task_published` → `incoming/005_task-pao-ack-20260816.json` |
| 배달 | watcher가 claim → `claimed/`, `leases/` 1건, heartbeat `running` + `current_task_id` |
| 실행 | `ack.txt` 11B, `echo.txt` 22B 기록 |
| 제출 | `status=succeeded`, `exit_code=0`, evidence에 commands + 두 바이트 수 |
| `collect --archive` | count 1, quarantined 0 |
| `validate` | `ready_for_oa_review`, 기계 체크 전부 통과, criteria 3건 `manual_check_required` |
| OA 독립 검증 | 파일을 바이트로 재확인 — `b'pao-ack-ok
'`, `b'task-pao-ack-20260816
'`, CR 없음 |
| `validate --record` | `semantic_verdict=accepted`, ledger `completed` |
| **복귀** | LWAR3가 `complete` 후 **같은 watcher를 재기동**해 `watching`으로 복귀, 전 채널 0 |

검증된 것:

1. **exit-notify 루프의 재시작 규율** — `complete` 후 재기동, 그 전에는 재기동하지 않음 (Rule 3 / P1 AdpLoopSplit).
2. **지시 준수** — `echo.txt`는 상수가 아니라 TaskContract의 `task_id`를 읽어 써야 통과한다. 이전 스모크(고정 문자열 ack)보다 강한 검사다.
3. **blind-safe** — `summary`/`evidence`에 런타임·모델·벤더 용어 없음 (Rule 10).
4. **OA 수용 규율** — `exit_code=0`만으로 승인하지 않고 파일을 바이트로 재검증한 뒤 `accepted` 기록.

검증되지 **않은** 것: 이종 벤더 동시 3-LWAR, 50분 슬라이스 경계, cancel/drain 경로, 축소 `slice_s`의 실제 동작.

---

## 11. P4 실행 기록 (2026-08-16)

### 추가된 명령 (protocol 1.4.2 유지 — 스키마 무변경)

`tombstones.schema.json`의 `entries`는 free-form object이므로 `retirement_mode: "unadopted_reap"` 추가에 스키마 변경이 필요 없다. D3(A) 결정이 코드 확인으로 뒷받침됐다.

| 명령 | 해결 | 펜스 |
|---|---|---|
| `recover --reclaim-unadopted` | R1 | tuple 일치, state ∈ {on,draining,off}, **해당 identity의 하트비트가 있으면 거부**(`identity_already_adopted`), `registered_at` 기준 age > `--unadopted-after`, 전 채널 공백. tombstone-first, 재실행 시 `already_reclaimed` |
| `recover --expire-controls` | R2 | tuple 일치, 매칭 하트비트가 신선하면 거부(`watcher_alive`), 임계 이하 control은 skip. **원본 바이트 보존** — `archive/control/`로 이동 + `.expired.json` 사이드카 |

이전 세대의 잔존 하트비트는 채택 증거로 취급하지 않는다(테스트로 고정). 이것이 R1이 실제 버스에서 막혔던 원인의 반대편이다.

### 게이트

| 게이트 | 결과 |
|---|---|
| `pytest tests/pao tests/if` | **64 passed** (기존 21 + IF 31 + 신규 12) |
| 신규 펜스 테스트 | `tests/pao/test_slot_reclaim.py` 12건 — 멱등, 채택 거부, 구세대 하트비트 무시, tuple 불일치, 신선 승인 거부, 활성 작업 거부, 원본 바이트 보존, 살아있는 watcher 거부 |
| 변경 모듈 md5 parity | `registry.py` / `oa_cli.py` 두 사본 동일 |
| `doctor` | oa/lwar 모두 healthy, **1.4.2 유지** |
| V8 (라이브 버스) | LWAR3에 두 명령 모두 fail-closed — `identity_already_adopted`, `watcher_alive`, `registry_version` 불변 |

### 실제 회수

| 슬롯 | 경로 | 결과 |
|---|---|---|
| LWAR2 | `--reclaim-unadopted` (`--unadopted-after 3600`) | 회수. `approval_age_s` 32953s. registry 14 → 15. 재실행 `already_reclaimed`, 버전 불변 |
| LWAR1 | `--expire-controls` → `--retire-stale` | 06:13:08Z `shutdown` 1건 만료(age 54998s) → 채널 전부 0 → 은퇴. registry 15 → 16 |
| LWAR3 | — | 무변경, `active`/`watching` 유지 |

최종: `registry_version` 16, **LWAR3 단독**, audit `healthy`, tombstone에 LWAR1(`stale_idle_reap`)·LWAR2(`unadopted_reap`) 세대 보존.

### 관측 — 설계 제약 정정

`registry.py` 하나로 "두 번들은 byte-identical"이라 단정했으나, `lwar_cli.py` / `adp_watch.py` / `pao_cli.py`는 **초기 커밋부터 이미 상이**하다(역할별 차이). parity 게이트는 **변경한 모듈에만** 적용한다. 기존 상이 3종은 이번 범위 밖이며 통일 대상이 아니다.

---

## 12. P5 실행 기록 (2026-08-16)

문서만 변경. 런타임 무변경.

### CompleteIdempotency — 코드가 이미 답을 갖고 있었다

`command_complete`는 claim 파일을 **소비**하고, 두 번째 호출은 `result_exists`로
`task already has a submitted result (already completed)`를, 아니면
`no claimed task to complete … superseded/requeued` 를 낸다. 즉 **재시도가 중복 결과를 만들 수 없다.**
codex P1이 지적한 "무재시도는 유실, 무조건 재시도는 중복"의 딜레마는 실재하지 않았고,
비결정적이었던 것은 문서뿐이었다.

문서화한 규칙: 제출 여부가 불확실하면 **같은 `complete`를 그대로 다시 실행하고 메시지로 분기**한다.
메일박스를 들여다보지 않고, 건너뛰지도 않는다. 4가지 메시지 → 행동 표를 추가했다.

이 규칙은 P2의 축소 슬라이스와 직접 결합한다 — 슬라이스가 짧아지면 재시작이 잦아지고
제출 근처에서 끊길 확률이 오른다.

### ExitCodeDictionary — 실측 대조

`lifecycle.md`에 LWAR 측 전 명령의 exit code를 한 표로 모았다. 코드에서 도출한 뒤 4건을 실제 실행으로 확인:

| 검사 | 실측 | 문서 |
|---|---|---|
| `oa-status` (OA live) | 0 | 0 |
| `status` (identity 파일 없음) | 1 | 1 |
| `status` (미등록 슬롯) | 3 | 3 |
| `complete` (claim 없음) | 1 + 정확한 메시지 | 1 |

`status` exit `1`(identity 파일 소실, qwen U4)은 §0.5 분기에 없던 상태였다 — REGISTER fresh로 규정했다.

### 나머지

- `PermissionGateStatus` — 호스트 권한 게이트 거부는 `blocked` + evidence에 거부된 명령. 무인 루프에서 lease 만료 방치보다 낫다
- `NextActionSpec` — 런타임 실제 값은 `validate` | `none`, **OA는 분기하지 않는다**(advisory). 코드 확인 후 그대로 명세화
- `CancelLimitNote` — P1에서 조기 완료

---

## 13. P6 실행 기록 · 설계 마감 (2026-08-16)

P6 개별 항목은 위생이지만, 묶어 보면 **"문서가 자기 번들을 잘못 기술하는"** 한 부류였다.

| 노드 | 고친 불일치 |
|---|---|
| ArgumentHintFix | `argument-hint`에 `adp`/`adp-stop`/`adp-wait` 누락, CLI verb가 아닌 `start`는 그냥 있었음 → `start (agent action, not a CLI verb)` |
| DanglingRefFix | `lifecycle.md`가 존재하지 않는 `(§1.3)` 인용 → `SKILL.md §1 Rule 6` |
| LegacyIdentityWording | "Legacy identities"가 **현행** 정본 위치를 가리켜 오판 유도 → canonical location으로 재서술 + "정본이라고 채택 가능한 건 아니다" 명시 |
| ConformanceNote | 번들에 있으나 어느 문서도 언급 0건이던 `conformance/` → SKILL.md 한 문단 + `conformance/README.md` 신설 (OA측 캘리브레이션 팩, LWAR는 실행 안 함) |
| MailboxLayoutSync | 실제 존재하는 `executions/` · `invocation.json` · `watcher.pid.json` 누락 → 반영 + 소유권(watcher vs agent) 명시 |
| LifecycleGraphFix | 선형 서술이 실제 그래프보다 좁음 → 전이 표(`on→off` 직행, `draining→on`, `off→on`) 추가. 이 복귀 간선이 slot 재개를 가능하게 한다 |
| MiscDocPack | `PAO_LWAR_IDENTITY` 폴백, schemas 목차(LWAR용/OA용 구분), watcher stdout 이벤트 JSON 예시, shebang 주의, `behavior_contract` 설명, `register [number]` 의미, blind-safe(툴 헤더·경로 유입), `identity_leaks` 센티널 오검출, monitor류 idle-kill 금지, `result_draft_path` 사용, 보고 템플릿 5줄 |

### 버전 확정

`SKILL.md` 헤더를 **v1.18**로 올리고, **스킬 버전과 프로토콜 버전의 관계**를 명시했다 — 호환 경계는 protocol `1.4.2`(register가 스탬프, OA가 fail-closed 거부)이고, 스킬 버전은 이 문서 세트를 추적한다. "runtime version이 바뀌면 재독"은 protocol 쪽을 가리킨다 (grok 1.3).

버전을 P6 **뒤**에 올린 이유: 헤더가 `v1.17`인데 내용이 다르면 벤더 세션이 "v1.17을 읽었다"고 보고하면서 다른 계약을 수행한다. 버전 문자열은 위생이 아니라 식별자다.

### 미완 — `ProbeScriptUpgrade` (designing 유지)

P2·P6 통틀어 유일하게 남긴 노드. `host_notify_probe.py`에 타임스탬프를 출력해 판정 근거를 세션 기억 밖에 남기자는 제안(deepseek F4)이다. 남긴 근거:

1. **유일한 코드 변경 항목**이고, 문서 계약이 검증된 지금 굳이 스크립트 표면을 늘릴 이유가 약하다.
2. `§1c stdout_on_kill`의 fail-closed 규칙이 **판정 불가 상황을 이미 안전한 쪽으로 흡수**한다 — 근거를 못 남기면 축소 슬라이스로 강등되므로, 타임스탬프가 없어서 생기는 급성 위험이 없다.
3. 실행하려면 양 번들 동시 반영 + probe 재검증이 필요한데, 그 비용을 지금 지불할 근거가 없다.

되살릴 조건: live-notify로 판정된 호스트가 처음 등장하거나, probe 판정이 실제로 틀린 사례가 관측되면.

### 설계 상태

`PaoLwarV118` 루트 `(done)`. D1–D37 중 이번 범위에서 다루기로 한 항목과 R1·R2 전부 종료.
