# HANDOFF — InquiryFoundry

세션 종료 시점: 2026-08-21 (OA = Claude Opus 5, 워크스페이스 `D:\InquiryFoundry`).
다음 세션은 이 파일을 먼저 읽고, 기본 역할은 **OA**다. 벤더 LWAR을 OA가 띄우지 않는다.

호칭: 정욱님. 한국어 응답, 코드/경로/식별자는 English. 로컬 스킬만 (`.agents/skills`).

**읽는 법.** §0 은 지금 유효한 정책이고 **반드시 읽는다.** §1–§6 은 현재 상태다.
**§7 은 사고 기록이며 시간순이라, 뒤에서 앞을 뒤집는 절이 있다** — 필요할 때 참조하되,
정책을 §7 에서 읽어 내지 말 것. 정책은 §0 에 있다.

---

## 0. 지금 유효한 정책

### IF 는 자기 예산을 모른다 (§7.12)

**IF 의 목적은 질문 생산이다. 그 질문을 우리가 실행할 수 있는지는 독립적이다.**
실행 가능성에는 두 가지가 섞여 있고 섞으면 안 된다:

| | 무엇인가 | 어디로 |
|---|---|---|
| **(A) 누구도 못 함** | 반증 조건이 비공개 소유 데이터로만 판정되고 공개 대체물이 없다 | 질문의 결함. 거부하고 회피 창에 싣는다 |
| **(B) 우리가 못 함** | 그 클러스터를 우리가 안 가졌다 | 우리의 사정. **`DEFERRED`** 가 자리다(`DEFERRED → SCORED` 로 복귀) |

- **브리프 `constraints` 에 예산·규모 제한을 넣지 말 것.** `constraints` 는 생성기에 전달되므로
  (B)를 넣으면 **질문이 우리 지갑에 맞춰 축소된다** — 실측된 사고다(§7.12).
  현재 유효한 3개 조항은 `_workspace/if-live9/brief.yaml` 이 기준이다.
- **`reason_kind`** 가 (A)/(B)를 가른다. `query_avoid_patterns` 는 `question_defect` 만 읽는다.
  `defer` 의 기본값은 `our_capacity`, 나머지는 `question_defect`.
- **`ADOPTED` 는 "추구할 가치가 있다" 이지 "지금 실행한다" 가 아니다.**

### 채택 판정은 Fable 5 에게 상시 위임돼 있다 (§7.13, 운영자 결정)

- 리뷰어는 **LWAR4 (Fable 5, anthropic)**. **생성 로스터에 넣지 말 것** —
  `request_review` 가 자기 산출물 리뷰를 거부한다.
- 리뷰어 패킷에는 **출처가 없다** — 벤더·연산자·기계 점수·선행 판정 모두 제외.
- **`ratify` 없이는 어떤 런도 마감되지 않는다.** `apply_recommendation` 이 `reviewer` 를
  비워 두고 `preflight_close` 가 거부한다. 이 보장은 리뷰어의 정직성에 의존하지 않는다.
- 위임 종결은 `ratify --delegated` 로 하고 `decided_by: delegated` 가 남는다.
  **`human_ratified`(사람이 읽고 서명) 와 구별해서 기록할 것** — 질문 품질이 흔들릴 때
  위임 종결과 상관되는지부터 물어야 한다.
- **`our_capacity` 판정은 Fable 이 구조적으로 못 내린다**(우리 자원을 모른다).
  채택분 중 지금 못 할 것을 `DEFERRED` 로 내리는 판단만 운영자에게 남는다.

### 인프라 실패는 품질 판정이 아니다 (§7.9, §7.10)

- 판정 카드 미도착 → **`DORMANT`**(회수 가능), 판정자의 `GATE_FAIL` → `REJECTED`.
- 회수 경로: **`rejudge`** (judge 라운드만 재실행) → **`reopen`**(닫힌 런에 회수분 추가)
  → `review-run` → `ratify` → `close`. `close` 는 기존 집계에 **더한다**.
- 수신 검증이 있으므로 YAML 인용 오류 같은 것으로 **런 전체가 죽지 않는다**.
  버려진 seed 는 `report.dropped_seeds`, 미판정은 `unjudged`, 반복은 `repeat_seeds` 에 남는다.

### 명령 요약

```bash
if_cycle.py run --brief B --if-root .if --pao --lwars L1:v1,L2:v2,L3:v3
if_cycle.py review-run --run R --if-root .if --lwar-id LWAR4 --by fable-5
if_cycle.py ratify --run R --if-root .if --reviewer "Jung Wook Yang" --delegated
if_cycle.py close --run R --if-root .if
if_cycle.py rejudge --run R --if-root .if --lwars ...   # 판정 못 받은 질문 회수
if_cycle.py reopen  --run R --if-root .if               # 닫힌 런에 회수분 추가
```

런 직전 로스터 확인은 **`oa.py status --busy-grace 960`** 로 하고,
정족수는 **`alive_count`**(합집합)로 본다 — `routable_count + busy_count` 는 중복 계산이다.

---

## 1. Git

- Remote: https://github.com/sadpig70/InquiryFoundry (public)
- Branch: `main` tracking `origin/main`. **HEAD = `4f6eb52`, push 완료** (워킹 트리 clean, 크래시 전 커밋 전부 반영됨)

  - `4f6eb52` if-core: enforce the vendor exclusion that was only declared
  - `2ce46b2` handoff: the alibaba exclusion is declared but never enforced
  - `2f8c900` design: three vendors, one contract, and what auto-routing did with them
  - `ced74f8` probe: timestamp the notify markers so the evidence outlives the session
  - `ff82a68` design: close the last unverified contract, and what a failed probe taught
  - `14acd5c` pao: give drain a documented way back, without touching the schema
  - `22b9f1d` pao: cancel cannot stop an in-flight task, and one fence was wrong because of it
  - `88edffb` design: record the first evidence for the shortened ADP slice
  - `e7507c2` pao-lwar: make the register-or-not trigger unambiguous

- 작업 브랜치 `pao-lwar-v1.18`은 fast-forward merge 후 삭제됨. 되돌릴 단위는 위 커밋들.

올리지 말 것: `.pao/`, `.if/`, `_workspace/`, `.env`, identity, mailbox. (`.gitignore`가 이미 처리)

**주의**: 통합 리뷰 원본 `_workspace/lwar-skill-review/*.md`는 **gitignore되어 리포에 없다**. 로컬에만 존재하며 설계 문서의 유일한 근거 자료다.

---

## 2. 역할 / 스킬

| 역할 | 스킬 | 비고 |
|---|---|---|
| OA (기본) | `.agents/skills/pao-oa/SKILL.md` v1.37 | `python .agents/skills/pao-oa/scripts/oa.py` + `.pao`만 |
| LWAR | `.agents/skills/pao-lwar/SKILL.md` **v1.18** | 벤더 세션에서 `/pao-lwar` |
| IF overlay | `if-oa`, `if-lwar`, `if-core`, `if-generate`, `if-contrarian`, `if-judge` | |

권위 설계: IF는 `.pgf/DESIGN-InquiryFoundry.md` v0.2.3. 스킬 개선 `.pgf/DESIGN-PaoLwarV118.md`은 **완료**(`ProbeScriptUpgrade` 1건만 `designing`).

Python: PATH의 `python`. Shell: Git Bash 또는 PS7 (`D:\Tools\PS7\7.6.4\pwsh.exe`). PS 5.1 금지.

---

## 3. 버스 / 등록 (지금)

- Bus: `D:\InquiryFoundry\.pao`
- `registry_version`: **39**. 슬롯 **4개**, 전원 `active`.

| 슬롯 | gen | profile | 역할 |
|---|---:|---|---|
| LWAR1 | 4 | Codex / `codex` / `openai` | 생성 |
| LWAR2 | 4 | Antigravity / `antigravity` / `google` | 생성 |
| LWAR3 | 4 | Grok Build TUI / `grok_build` / `xai` | 생성 |
| LWAR4 | 3 | Claude Code / `claude_code` / `anthropic` (Fable 5) | **리뷰어 — 생성 로스터에 넣지 말 것** |

  IF 런은 `--lwars LWAR1:openai,LWAR2:google,LWAR3:xai` 로 돌린다. 벤더 3종이라
  `normal` 모드의 "2종 이상" 을 만족한다. 배제 정책(`EXCLUDE_FAMILIES={alibaba}`,
  `EXCLUDE_ADAPTERS={qwen}`)에 걸리는 것은 없다.

- **슬롯 번호는 재사용된다.** 지금까지 은퇴한 것: alibaba(고아), moonshot·zai(크레딧 소진),
  deepseek(운영자 종료), xai(정규 해지 후 재등록). 과거 런의 벤더를 현재 레지스트리로
  읽으면 틀린다 — 그 런의 `allocation.yaml` 이 기록이다.
- **크레딧 소진이 두 번 일어났다**(moonshot, zai). 런 완주에 20~45분이 걸리고 그동안
  3대가 살아 있어야 하므로, 세 번째도 온다고 보고 `rejudge`/`reopen` 경로를 유지할 것.
- audit `healthy`, degraded/pending 0.

다음 OA: `PAO_OA_ID` mint(또는 직전 id 재사용) → `presence` → `reconcile` → `status`.
writer lease / `.command.lock` 손삭제 금지.

---

## 4. ADP 계약 (이번 세션에서 개정됨) — 필수

**공식 경로는 exit-notify다.** `SKILL.md` §2 "Canonical commands by `notify_style`" 표가 **명령의 단일 출처**이며, 다른 문서와 충돌하면 이 표가 이긴다. 우선순위: **adapter 제약 > probe 결과 > 일반 기본값**.

| 이름 | 의미 | Watcher |
|---|---|---|
| **exit-notify** (기본) | 종료 후에야 stdout | `scripts/adp_exit_notify.py` / `lwar.py adp` |
| **live-notify** | 프로세스 살아 있는 동안 stdout을 **호스트가 세션에 밀어넣음** | `scripts/adp_live_notify.py` / `lwar.py adp-live` |

프로브가 기록할 값이 **3개로 늘었다** (`references/host-notify-probe.md` §1):

1. `bg_timeout_50m` — 옵션 수용. "문서화된 3000s 미만 상한 = fail", "무제한 background + 종료 시 stdout 전달 = pass"
2. `host_blocking_cap_s` — **블로킹 상한**. `slice_s = max(60, cap − 60)`을 `--max-runtime-s`로 넘긴다. 600s 호스트 → **540**. 프로토콜은 안 변하고 재시작 빈도만 변함
3. `stdout_on_kill` — 불명이면 false 취급

**live-notify는 "폴링 없이 호스트가 깨우는" 경우만이다.** 스냅샷/`TaskOutput`으로 **요청해야** 보이는 출력은 exit-notify. 실측 8개 런타임 중 live-notify는 **0건**.

호스트 능력 매트릭스(실측 8종) + `adapter_id`/`interface` 슬러그 카탈로그: `references/host-adapter.md`.

금지: `lwar3_adp_loop.py`, `capture_output=True` 래퍼, `--detach`를 주경로, mailbox JSON 손삭제, 재등록(유효 identity일 때).
**추가**: 실작업 의도 없는 세션(리뷰·평가·진단)은 `register`하지 않는다 (§0.5). `registration_pending` 재시작은 유한 (Rule 13).

---

## 5. 계약 검증 — `task-pao-ack-20260816`

P1~P2 개정이 실제로 작동하는지 확인한 **첫 end-to-end 실행**. `send` → claim → `begin`/실행/`complete` → **watcher 재기동** → `collect --archive` → `validate --record accepted` → ledger `completed`.

- `echo.txt`가 TaskContract의 `task_id`를 읽어 써야 통과하도록 설계 — 고정 문자열 ack보다 강한 지시 준수 검사
- OA가 `exit_code=0`만으로 승인하지 않고 파일을 바이트로 재검증한 뒤 `accepted`
- 상세: `.pgf/DESIGN-PaoLwarV118.md` §10

추가 검증 (`task-pao-ack2-20260818`, Qwen LWAR1): `count.txt`로 계약 역참조까지 요구한 강화 probe 통과.
sha256 자가보고 3건이 OA 재계산과 일치. **축소 `slice_s` 실증** — watcher 명령줄에 `--max-runtime-s 540`,
슬라이스 간격 551초(540 + 재시작 ≈11초), `adp_error` 0건. **50분 슬라이스**도 LWAR3가 31슬라이스 25시간 무중단으로 검증.

**cancel 경로 실증 완료** (§6 참조): 실행 중 cancel은 **태스크를 멈추지 못한다**(정상 완료됨).
미claim 태스크 cancel은 tombstone으로 완벽 동작(발행→취소 6초).

`drain` 경로: **D38을 (B) 문서 규약으로 해소** — `oa.py control --command ping --reason "pao-resume: …"`.
`draining` LWAR이 이를 받으면 `state on`을 요청한다(`lifecycle.md`). 전달 계층은 실증했으나 **resume 동작 자체는 미검증**:
현 LWAR1·LWAR3는 이 규약 이전에 번들을 읽었으므로 이해하지 못한다. **다음 신규 등록부터 유효.**
그 전까지 `drain`은 여전히 되돌릴 수 없으니 **멈출 의도가 아니면 걸지 말 것.**

---

## 6. 새 OA 명령 (protocol 1.4.2 유지)

`references/recover-maintain.md` 참조. 둘 다 기존 경로와 같은 펜스 강도이며 **살아있는 LWAR에 fail-closed**임을 라이브 버스에서 확인했다.

```bash
oa.py recover --reclaim-unadopted --lwar-id LWARn --instance-id … --generation N --unadopted-after 3600 --reason "…"
oa.py recover --expire-controls    --lwar-id LWARn --instance-id … --generation N --control-older-than 600 --reason "…"
```

- `--reclaim-unadopted` — 승인됐으나 **identity 미채택** 슬롯. 해당 identity의 하트비트가 있으면 `identity_already_adopted`로 거부. 재실행 `already_reclaimed`
- `--expire-controls` — 죽은 watcher 앞 미수령 control. 원본 바이트 보존(`archive/control/` + `.expired.json` 사이드카). `retire-stale`이 `active_work: {"control": N}`로 막힐 때 **먼저** 실행.
  나이와 무관하게 `running`/`current_task_id`면 `watcher_busy`로 거부한다 — **exit-notify에서 실행 중인 LWAR은 heartbeat이 얼어붙어 stale로 보이기 때문**이다(2026-08-18 실측 후 수정)

> **주의**: `runtime_status=stale`이 곧 죽음은 아니다. exit-notify watcher는 태스크를 배달하며 종료하므로,
> 에이전트가 실행하는 동안 heartbeat이 `running` + `current_task_id`인 채 갱신되지 않는다.
> 120초(기본 `--stale-after`)보다 긴 태스크는 정상 동작 중에도 stale로 보인다. `status`와 `current_task_id`를 함께 볼 것.

**런타임 사본 주의**: `pao_runtime/`은 두 스킬에 중복 배치돼 있다. `registry.py`/`oa_cli.py`는 byte-identical로 유지해야 한다. 단 `lwar_cli.py`/`adp_watch.py`/`pao_cli.py`는 **초기 커밋부터 이미 역할별로 상이**하며 통일 대상이 아니다. `runtime_version`을 한쪽만 올리면 모든 신규 등록이 `runtime_version_mismatch`로 거부된다.

---

## 7. 라이브 IF 런

| Run | 상태 |
|---|---|
| `RUN-20260814-live1` | **동결**. judge 연결 금지. dead-letter 1건(`…contrarian-LWAR3-r0`)은 requeue 금지 |
| `RUN-20260815-live2` | generate/contrarian/judge 3/3, compose 완료. `protocol_valid=true`, SCORED 8, REJECTED 1. human=`awaiting_human`. **ADOPTED는 인간만** |
| `RUN-20260818-live3c` | **종결** (2026-08-19). `--pao` 정규 경로 최초 완주(8분) + **`close` 최초 실행**. seed 9 / qo 9 / scored 9, `protocol_valid`·`hypothesis_valid`·`dissent_referenced` 모두 true, `contributing_generate_lwars=3`. human=`closed`, `decided: {adopt 4, reject 5, defer 0}`. reviewer `Jung Wook Yang`. **이 저장소에서 EXPLORE→EXPLOIT→REVIEW→CLOSE 전 구간을 완주한 첫 런** |
| `RUN-20260822-live12` | **종결** (2026-08-22). `adopt 4 / reject 5`. `repaired_seeds` 5 / `repeat_seeds` 0. **G-GROUND 실패 2건 — 코퍼스 밖 인용 시도**(소진 신호). pattern 5건이 쌓였으나 어휘 불일치로 **등록부 등재 0**(§7.18) |
| `RUN-20260822-live11` | **종결** (2026-08-22). `adopt 6 / reject 2 / defer 1`. `repaired_seeds` 4 / `repeat_seeds` 0 / 새 영역 5. **`pattern` 과 쓰기 린트가 처음 발동**했고 거부 2건 모두 수치 없는 구조 서술로 왔다. 등록부는 2런 등재 조건이라 아직 비어 있다(§7.17) |
| `RUN-20260822-live10g` | **종결** (2026-08-22, `adopt 9 / reject 0`, §7.16). 완주, `human=awaiting_human` (2026-08-22). live8 과 배정이 동일하도록 `brief_id` 를 골라 세운 통제 비교. seed 9 / qo 9 / scored 9, 9/9 succeeded, 손실 0. **예산 조항을 빼도 `OP-SCALE` 규모가 돌아오지 않았다** — 오염원이 브리프에서 회피 창으로 이동했다(§7.14) |
| `RUN-20260821-live9` | **완주**, `human=awaiting_human` (2026-08-21). 예산 조항을 뺀 `constraints` 로 돌린 첫 런. seed 9 / qo 9 / scored 9, 9/9 succeeded, `dropped_seeds`·`unjudged`·`repeat_seeds` 모두 0. **`OP-2ND`/`OP-REGIME`/`OP-ADV` 첫 등장**(연산자 회전). 핵심 지표 `OP-SCALE` 은 회전 때문에 배정되지 않아 측정 실패(§7.12). 자료 `_workspace/if-live9/review-brief.md` |
| `RUN-20260821-live8` | **완주**, `human=awaiting_human` (2026-08-21). 로스터 codex/openai · antigravity/google · **grok/xai**(신규). seed 9 / qo 9 / scored 9, 9/9 succeeded, `dropped_seeds` 0, `unjudged` 0 — 손실 없는 첫 런. 제약 효과 재현(자원 초과 0건, 등가 마진 9/9). **LWAR2 가 live7b 문항 3건을 유사도 1.00 으로 재생성** — `--pao` 경로에 중복 억제가 없다(§7.10). 자료 `_workspace/if-live8/review-brief.md` |
| `RUN-20260820-live7b` | **완주(손상)**, `human=awaiting_human` (2026-08-20). 브리프 `constraints` 3건을 처음 투입한 런. seed 9 / qo 9 / **scored 5**, `protocol_valid` true 이나 `slo_scored_ge_8` false — GLM 크레딧 소진으로 judge 1건 타임아웃. 제약 효과: 자원 초과 설계 9/9 해소, 기각 조건 9/9 등가 마진(§7.10). 판정 못 받은 4건은 `DORMANT` 로 복구(§7.9). 검토 대상 **5문항**, 자료 `_workspace/if-live7/review-brief.md` |
| `RUN-20260820-live6` | **종결** (2026-08-20). 코퍼스 확장 후 첫 런. seed 9 / qo 9 / scored 9, `protocol_valid` true, 9/9 succeeded, 이탈 0. 근거 18건 중 신규 후속 문헌이 12건. `decided: {adopt 3, reject 5, defer 1}` — **live3c 이후 첫 채택**이고 live5b 의 9/9 거부에서 크게 개선됐다. 채택 Q-0015/0016/0017, 유보 Q-0013. 효과·남은 패턴·리뷰어 관측은 §7.8 |
| `RUN-20260820-live5b` | **종결** (2026-08-20). 새 로스터(codex/openai, antigravity/google, opencode/zai)로 **첫 시도 완주**, 이탈 0. seed 9 / qo 9 / scored 9, `protocol_valid`·`hypothesis_valid` true, `separation: full`, 9/9 succeeded. 인간 리뷰 결과 `decided: {adopt 0, reject 9, defer 0}` — **9건 전부 거부**. 사유는 전부 구체적 문헌 근거를 동반한다. 원인은 개별 질문이 아니라 코퍼스 구조다(§7.7) |
| `RUN-20260819-live5` | **실패** — `BLOCKED: protocol_incomplete` (2026-08-19). 과학적 실패가 아니라 인프라 실패다. LWAR5가 `generate` claim을 쥔 채 05:33에, LWAR4가 `judge` claim을 쥔 채 06:03에 침묵했다(턴 소진). 두 태스크는 리스 만료 후 dead-letter 됐고, 반론 없는 seed가 남아 compose가 막혔다. LWAR6(xai)만 3단계 완주. **측정 3(전 슬롯 7건 전량)은 라이브 `allocation.yaml`로 확정**, 측정 1·2는 질문이 확정되지 않아 답할 수 없다 — 특히 live4b에서 재발 2건을 만든 LWAR5가 아무것도 내지 못했다. 잔해는 `recover --delivery-timeout` 2회로 정리(dead-letter 4건, requeue 금지) |
| `RUN-20260819-live4b` | **종결** (2026-08-19). seed 9 / qo 9 / scored 9, `protocol_valid`·`hypothesis_valid` true, `separation: full`, `observed_statuses` 9/9 succeeded. 3사(deepseek/moonshot/xai) + `--pao` 경로 **2회 연속 성공**. human=`closed`, `decided: {adopt 5, reject 3, defer 1}` — 운영자 표와 **정확히 일치**(informational 0건이라 live3c 같은 집계 차이가 없다). reviewer `Jung Wook Yang`. 검토 자료 `_workspace/if-live4/review-brief.md` |
| `RUN-20260819-live4` | 중단됨(`PAO_OA_ID` 미설정으로 첫 `send`에서 fail-closed). 버스 부작용 0. `allocation.yaml` 이 되먹임 도달의 증거라 보존 |
| `RUN-20260818-live3` / `live3b` | 중단됨. 결과·question_id·버스 부작용 0. 아래 버그 2건의 증거로 보존 |

데이터: `.if/runs/…` (git 제외).
기계 게이트: G-GROUND, G-CLEAR, G-PATH, G-TESTSHAPE. D18–D21 유효.

### `close` 경로와 `informational` 의 실제 의미 (2026-08-19)

`if_cycle.py close --run <RUN_ID>` 도 이번이 최초 실행이다(플래그는 `--run`, `--run-id` 아님).

- **`informational` 은 독립 판정이 아니다.** `close_review` 는 `informational: true` 항목을
  `decision: reject` + `informational: True` 로 **decisions 로그에만** 기록하고,
  질문의 `status` 는 전이시키지 않는다(`SCORED` 유지). 운영자 판정 INFORMATIONAL 1건은 그래서
  `report.decided.reject` 에 합산되어 **adopt 4 / reject 5** 로 집계된다 — 운영자 표의 `REJECT 4` 와 수가 다른 것은 이 때문이며 오류가 아니다.
- `preflight_close` 게이트: `reviewer` 필수, `decision=pending` 또는 빈 `reason` 금지,
  그리고 **`wound`/`kill` 을 받은 질문은 전부 `dissent_portfolio` 에 등재돼 있어야** 한다(`dissent_not_referenced`).
- `query_avoid_patterns` 가 `reject` 사유를 도메인별로 읽어 **다음 런의 `avoid_patterns` 로 되먹인다.**
  따라서 `reason` 은 사후 감사용 메모가 아니라 다음 런의 입력이다.

### 되먹임 실증 — RUN-20260819-live4b (2026-08-19)

되먹임이 실제로 작동하는지 같은 `scaling` 도메인으로 2회차를 돌려 측정했다.

**결과: 경로는 작동하고, 배정이 실패했다.**

| 거부된 함정(live3c) | 사유를 **받은** LWAR | 재발 | 재발시킨 LWAR |
|---|---|---|---|
| Q-0007 1000배 스케일 조작 | LWAR6 | **예** (신 Q-0004) | **LWAR5** |
| Q-0008 통계역학 수입 | LWAR4 | **예** (신 Q-0005) | **LWAR5** |
| Q-0002 표본효율/계산최적 혼동 | LWAR4 | 아니오 | — |
| Q-0006 데이터 재사용 반사실 | LWAR5 | 아니오 | — |

**회피 신호를 받은 생성자는 4/4 그 함정을 피했고, 받지 못한 생성자는 2/2 재현했다.** 예외 없음.
재발 2건은 문구까지 거의 동일했고, 기계 점수 최하위 2위(0.613 / 0.458)로 앉았다 —
live3c의 원본 2건(0.650 / 0.485)과 거의 같은 값이다.

원인은 `build_allocation` 의 `avoid[i::len(lwars)]` stride 분할이었다. 4건이 2/1/1로 쪼개져
어느 생성자도 전체를 못 보고, 배정은 **내용과 무관하게 인덱스 순서**가 정했다.
`operators`/`evidence_kind`/`objective` 는 다양성 손잡이지만 **인간이 이미 거부한 함정은 아니다.**
전량 배포로 교체함(커밋 `61986b7`). 진단이 맞았는지는 3회차(live5)에서
같은 두 함정이 사라지는지로 확인한다 — **아직 확인되지 않았다.**

부수 결함 1건도 같이 잡았다: `query_avoid_patterns` 가 `informational` 을 걸러내지 않아,
"기록으로 남겨라" 판정의 사유가 다음 런에 **"피하라"** 로 전달되고 있었다(커밋 `680c376`).

### 턴 소진은 claim을 좌초시킨다 (2026-08-19, live5에서 실측)

exit-notify LWAR의 턴이 끝나면 ADP가 멈춘다는 것은 이미 알려져 있었다
(adp-loop.md "When the turn ends anyway"). live5가 보여준 것은 **그것이 idle 공백에
그치지 않는다**는 점이다. 태스크를 claim한 상태로 끊기면 그 태스크가 좌초한다:
리스가 만료되고, OA가 재전달하고, 아무도 잡지 않아 dead-letter 되고,
런은 단계마다 타임아웃을 다 기다린 끝에 죽는다. live5는 45분을 그렇게 썼다.

`oa status` 의 busy 펜스는 **상한이 있어야 한다.** 처음 넣었을 때는 상한이 없어
좌초한 두 LWAR을 45분 내내 정상으로 보고했다. claim 리스는
`max(default_lease_s, task timeout + margin)` 이므로 그보다 한참 지난 `running` 은
작업 중이 아니다. `--busy-grace`(기본 1800s)가 경계이고, `needs_operator` 는
`held_task_id` 로 **어느 태스크가 묶였는지** 알린다.

`routable_count` 와 `busy_count` 는 **겹친다** — 실행 중에도 heartbeat를 갱신하는
런타임은 둘 다에 든다(2026-08-20 로스터가 그렇다). 정족수는 **`alive_count`**(합집합)로
보라. 둘을 더하면 3대짜리 로스터가 6으로 계산된다.

**런 중 감시는 태스크 타임아웃에 맞춘 grace로 하라.** 기본 1800s는 900s 태스크보다
길어서 좌초를 30분 뒤에야 잡는다. IF 런(900s)이면 `--busy-grace 960`.

### ⚠ live5 해석의 교란 요인 (live4b 종결 후 발생)

live4b가 닫히면서 회피 창이 4건 → **7건**이 됐고, 재발했던 두 함정은 이제
**사유를 2건씩** 갖는다(live3c 것 + live4b 것). 즉 live5에서는 두 가지가 동시에 바뀐다:

1. 전량 배포(`61986b7`) — 모든 생성자가 전체 목록을 본다
2. 신호 세기 — 두 함정에 대한 사유가 각각 2배

따라서 **live5에서 두 함정이 사라져도 원인을 하나로 귀속할 수 없다.**
분리 검정은 live4b가 새로 만든 함정에 있다: `Q-20260819-0007`
(Kaplan/Hoffmann 상호배타를 선결적으로 가정) 은 **사유가 1건뿐**이다.
전량 배포만으로 충분하다면 이것도 재발하지 않아야 한다. 재발하면 배포는
필요조건이었을 뿐 충분조건이 아니다.

`query_avoid_patterns` 의 창은 `n=8` 이다. 현재 7건이므로 **다음 종결부터 live3c 사유가
밀려나기 시작한다.** 오래된 함정의 재발 여부를 계속 보려면 창 크기를 재검토해야 한다.

`decisions.jsonl` 은 1회 압축했다. 사유 없이 넣었던 자리표시 reject 4건이 되먹임 창의
절반을 차지해 제거했고(백업 `.if/memory/decisions.jsonl.bak-20260819`), 인간 판정 자체는
`review.yaml` 과 실질 사유 레코드에 온전하다. **append-only 원칙을 깬 유일한 예외이며 반복하지 말 것.**

### `if_cycle.py --pao` 정규 경로는 한 번도 실행된 적이 없었다 (2026-08-18 수정)

live1/live2 는 `_workspace/if_autorun.py` 등 **금지 목록에 오른 우회 스크립트**로 구동됐다.
그래서 정규 경로에 버그 2개가 그대로 남아 있었고, live3 에서 처음 드러났다.

1. **`bus.py` 경로 off-by-one** — `oa_script()`/`lwar_script()` 가 `parents[3]`(`.agents`)을 써서
   `.agents/pao-oa/scripts/oa.py` 라는 없는 경로를 호출, 첫 `send` 에서 즉시 사망.
   스킬 루트는 `parents[2]`(`.agents/skills`)이며 **같은 파일의 다른 두 곳은 이미 맞게 쓰고 있었다.**
   → `_skills_root()` 로 통일.
2. **`publish_collect` 의 status 오파싱** — `oa collect` 는 ResultContract 를 `result` 아래에 중첩하는데
   코드가 봉투에서 `res["status"]` 를 읽어 항상 `""` 가 나왔다. 그래서 `succeeded` 분기에 진입하지 못하고
   `pending` 이 비지 않아, **3대가 3분 만에 정상 제출했는데도 15분 데드라인까지 기다린 뒤 `timed_out`** 으로 보고했다.
   `observed_statuses: ['','','','timed_out','timed_out','timed_out']` 의 빈 문자열 3개가 그 증거다.
   → `res["result"]["status"]` 우선으로 수정(기존 평면 형태도 폴백 유지).

회귀 테스트 2건(`tests/if`): 스크립트 경로 실재 확인, 그리고 **실제 collect 응답 형태를 주입**해 `succeeded` 파싱 검증.

> 교훈: 금지된 우회로만 쓰이면 정규 경로의 결함은 발견되지 않는다. live1/live2 가 "성공"이었던 것이
> 정규 경로의 건전성을 뜻하지 않았다.

### Qwen/`alibaba` 배제 — **강제됨** (2026-08-18)

`if-core/if_core/const.py`의 `EXCLUDE_FAMILIES = {"alibaba"}` / `EXCLUDE_ADAPTERS = {"qwen"}` 는
**정의만 되어 있고 어디서도 참조되지 않는 죽은 설정이었다.** `const.py`만 읽으면 "코드가 막아준다"고 오판하기 쉬웠고,
실제 방어선은 `if_cycle.py --lwars`에 무엇을 적느냐뿐이었다.

이제 `cycle.reject_excluded()` 가 `inquiry_cycle` 진입부에서 강제한다.

- **필터가 아니라 거부다.** 로스터에서 조용히 빼면 3-LWAR 런이 2-LWAR로 바뀌어 heterogeneity 검사의 의미가 달라진다.
  로스터는 운영자가 넘기므로 운영자가 고친다. 위반자를 **전부 이름으로** 지목한다.
- 가족(`FAMILY_NORM` 정규화 후)과 `adapter_id` 둘 다 검사한다. 실서비스 `adapter_id`는 `qwen_code`인데
  `EXCLUDE_ADAPTERS`에는 `qwen`만 있으므로 **가족 검사가 실제로 잡는 쪽**이다 — 두 검사 모두 유지할 것.
- 회귀 테스트 7건 추가(`tests/if`). 다시 죽으면 테스트가 깨진다.
- e2e 픽스처 5건의 `LWAR3: alibaba` → `xai` 로 교체, `if_cycle.py` CLI 도움말 예시도 교체(정책과 모순이었다).

> ### `normal` 모드는 alibaba를 뺀 **3대**를 요구한다 — 해소됨, 그러나 상시 조건
>
> `normal` 모드는 `>= 3 LWAR`를 요구하고(`cycle.py:347`) LWAR1(alibaba)은 배제되므로,
> **alibaba가 아닌 LWAR 3대**가 동시에 살아 있어야 IF 런이 선다.
> live3c·live4b는 `LWAR4 deepseek / LWAR5 moonshot / LWAR6 xai` 로 성립시켰다.
> 한 대라도 stale이면 `Blocked` 이므로 런 직전에 `oa status` 로 `runtime_status: active` 를 확인할 것.
> OA는 LWAR를 띄울 수 없다 — 정욱님이 해당 벤더 세션에서 `/pao-lwar` 를 실행해야 한다.
> `mode`를 낮추는 선택지도 있으나 그것은 IF 설계의 결정이다.

---

## 7.5 하드 크래시 복구 — `.pao-*.tmp` 잔해 (2026-08-18 실제 발생)

전원 차단으로 컴퓨터가 다운되면 **`doctor`가 unhealthy가 되어 버스 전체가 잠긴다.** 절차를 모르면 재기동이 불가능하다.

### 무엇이 남는가

`common.atomic_write_json()` 은 `NamedTemporaryFile(prefix=".pao-", suffix=".tmp")` → `fsync` → `os.replace` 순서로 쓰고,
`finally` 에서 임시 파일을 지운다. **하드 크래시는 그 `finally` 를 실행시키지 않는다.**
결과로 `.pao/mailbox/LWARn/.pao-XXXXXXXX.tmp` 고아가 남는다.

### 왜 치명적인가

- `doctor` 의 `no_leftover_tmp` 체크가 **일정 나이 이상의** `.pao-*.tmp` 를 발견하면 unhealthy 를 반환한다.
- 계약상 **OA·LWAR 모두 `doctor` 실패 시 중단**한다 → 어떤 LWAR도 재기동할 수 없고 OA도 버스를 변경할 수 없다.
- **이 파일을 지우는 CLI 경로가 없다.** `prune` 의 대상은 `archive/*`, `failed`, `quarantine`, `cancelled` 뿐이고
  `doctor` 는 보고만 한다. 즉 무해한 잔해 하나가 버스를 영구히 잠근다.

### 복구 절차 (실제 수행 검증됨)

```bash
# 1. 무엇이 남았는지 확인
python .agents/skills/pao-oa/scripts/pao.py doctor --role oa      # detail 에 경로가 나온다
find .pao -name ".pao-*.tmp"

# 2. 내용을 반드시 확인한다 — 지우기 전에 무엇인지 알아야 한다
cat .pao/mailbox/LWARn/.pao-XXXXXXXX.tmp
cat .pao/mailbox/LWARn/heartbeat.json      # 대개 heartbeat 쓰기 도중이다

# 3. 커밋본과 어느 필드가 다른지 비교. last_seen 만 다르면 순수 중복본이다
# 4. 증거를 백업한 뒤 삭제
# 5. doctor 재확인 → healthy
```

**판단 기준**: 커밋본이 유효하고 tmp 가 그 중복본이면 삭제해도 정보 손실이 0이다.
tmp 가 `result.json` / `task` / `registry` 계열이면 **삭제하지 말고 내용을 먼저 보고**할 것 — 그건 다른 사건이다.

### 2026-08-18 사례

`LWAR2/.pao-x6to70i8.tmp` = 크래시 순간 진행 중이던 heartbeat 쓰기.
tmp `last_seen=05:52:02.435874Z` vs 커밋본 `05:51:57.286903Z` (폴링 주기 5초 차),
그 외 전 필드 동일. 백업 후 삭제 → `doctor` 양쪽 healthy 복구.

**손실 0이었다**: 크래시 순간 3대 모두 유휴(`watching`/`current_task_id=None`), 전 큐 채널 공백,
마지막 커밋(`4f6eb52`)은 크래시 19분 전에 push 완료, `pytest` 73 passed 재확인.

### 해소됨 — `doctor --clear-leftover-tmp` (2026-08-18)

이제 정리 경로가 있다. **플래그 없이는 현행과 동일하게 아무것도 지우지 않는다.**

```bash
python .agents/skills/pao-oa/scripts/pao.py doctor --role oa --clear-leftover-tmp
```

**지우는 것은 단 하나** — `schema_version=pao.heartbeat.v1` 이고, 같은 디렉터리의 `heartbeat.json` 이
존재·파싱되며 `lwar_id`/`instance_id`/`generation` 이 일치하는 경우다. 그때 커밋본이 권위이고 tmp 는 중복본이다.

**나머지는 전부 보존하고 이유와 함께 보고한다** — `unparseable`, `not_a_heartbeat:<schema>`,
`no_committed_heartbeat`(tmp 가 유일본일 수 있다), `identity_differs_from_committed`, `became_recent`, `unlink_failed:*`.
즉 `result`/`task`/`registry` 계열 고아는 **여전히 doctor 를 막으며 사람의 판단을 요구한다** — 그것이 의도다.

정리된 항목은 audit 에 `leftover_tmp_cleared` 로 기록된다(조용한 삭제 없음).
회귀 테스트 10건: `tests/pao/test_leftover_tmp.py`.

---

## 7.6 claim을 쥔 채 죽은 런타임의 슬롯 (2026-08-19)

런타임이 태스크를 claim한 상태로 사라지면 heartbeat가 `running` +
`current_task_id` 로 얼어붙는다. `retire_stale` 은 이를 `heartbeat_not_idle` 로
거부하는데, **그 상태를 풀 방법이 원래 없었다.** 런타임이 죽었으니 스스로
`retire` 할 수 없고, `--reap-startup`(starting 전용)도
`--reclaim-unadopted`(미채택 전용)도 해당하지 않는다. claim이 이미 dead-letter 되고
메일박스 6개 큐가 전부 비어도 슬롯은 영구히 묶인다.

R1(미채택 슬롯)·R2(미수령 control)와 같은 형태다 — 흔한 경우엔 옳은 관문인데
실제로 발생하는 상태에 탈출구가 없는 것. 같은 방식으로 고쳤다(커밋 `c865d69`):
기본 관문은 그대로 두고 **별도 펜스를 가진 명시적 경로**를 추가했다.

```bash
oa.py recover --retire-stale --lwar-id LWAR5   --instance-id INSTANCE_ID --generation GENERATION   --expected-last-seen TIMESTAMP --stale-after 120   --abandoned-task-id TASK_ID --reason "..."
```

- `--abandoned-task-id` 는 **heartbeat가 가리키는 바로 그 태스크 id**여야 한다.
  틀린 id는 플래그를 안 준 것과 똑같이 `heartbeat_not_idle` 로 거부된다.
- 일반 `active_mailbox_work` 검사는 그대로 남는다. 진짜 실행 중인 런타임은
  `claimed` 항목과 살아 있는 lease를 갖고 있으므로 `active_mailbox_work` 로 거부된다.
- 묘비에 `retirement_mode: stale_abandoned_claim_reap` 과 `abandoned_task_id` 가 남는다.

**선행 조건 — `collect --archive` 를 먼저 돌려야 한다.** IF 사이클은 `collect` 를
`--archive` 없이 호출하므로 배달 완료된 결과가 `outgoing/` 에 쌓이고,
`_active_mailbox_work` 가 이를 활성 작업으로 세어 은퇴를 막는다. 결함이 아니라 설계다.

---

## 7.7 코퍼스 지평선 — live5b가 9/9 거부된 진짜 이유 (2026-08-20)

live5b는 프로토콜상 완벽했다(`protocol_valid: true`, 이탈 0, 9/9 succeeded).
그런데 인간 리뷰에서 **9건 전부 거부**됐고, 사유 9건 중 6건이
"이미 답이 나옴" 또는 "전제 소멸"이었다 — Muennighoff 2023, Sardana & Frankle 2023,
Porian 2024 등 **2023–2024 후속 문헌이 이미 닫은 갭**을 미지로 오인해 질문을 만든 것이다.

리뷰어의 배치 진단: *"근거 코퍼스가 2020/2022 두 논문뿐이라, 두 논문 사이의 갭을
미지로 오인했다."* 이것은 증상 기술이고, **기전은 게이트에 있다.**

`mechanical_gates` 의 `G-GROUND` 는 모든 `evidence[].source` 가
`evidence_hints` 의 문자열과 일치할 것을 요구한다(`gates.py:21`, `source_in_hints`).
`_workspace/if-live5/papers.txt` 는 **두 줄**이고 `evidence_hints.papers` 도 두 항목뿐이었다.
따라서 생성기가 Muennighoff 2023 을 알고 인용하려 해도 **그 seed 는 G-GROUND 에서
탈락한다.** 파이프라인은 후속 문헌을 모르는 것이 아니라 **인용이 금지돼 있었다.**

즉 이것은 생성 품질 문제가 아니라 **코퍼스 지평선을 게이트가 강제한 결과**다.
형식 게이트를 더 붙여도 고쳐지지 않는다. 고칠 곳은 `evidence_hints` 다.

리뷰어의 부수 지적: 측정 불가능한 이름뿐인 변수가 3건(Q-0002/0003/0005).
"변수는 기존 문헌에 측정 절차가 존재하는 것만 허용" 제약은 코퍼스를 넓히면
일부 자연 해소되지만(측정 절차가 있는 논문을 인용할 수 있게 되므로) 별개 사안이다.

### 회피 창이 비워졌다

`query_avoid_patterns` 의 창은 `n=8`. 이번 9건 거부로 **live3c·live4b 의 7개 함정이
전부 밀려났고**, live5b 자신의 첫 사유(Q-0001)까지 함께 잘렸다. 현재 창은
live5b 사유 8건뿐이다. 1000배 스케일·물리 유비·모순 선결가정 함정은 더 이상
다음 런에 전달되지 않는다 — **한 번의 대량 거부가 축적된 신호를 통째로 지운다.**

## 7.8 코퍼스 수리와 그 효과 — live6 (2026-08-20)

> **⚠ 이 절의 `constraints` 관련 결론은 §7.12 에서 뒤집혔다.**
> 코퍼스 확장(`evidence_hints` 2편 → 6편)은 유효하고 지금도 그대로 쓴다.
> 그러나 여기서 도입한 **브리프 `constraints` 의 예산·규모 조항은 오염이었다** —
> 질문이 우리 지갑에 맞춰 축소됐고 §7.12 에서 제거했다.
> **이 절만 읽고 "제약이 효과적이니 더 넣자" 고 판단하지 말 것.**


§7.7 진단대로 `evidence_hints.papers` 를 2편 → **6편**으로 넓혔다.
브리프는 `_workspace/`(git 제외)에 있으므로 **코퍼스 구성은 여기에만 기록된다:**

```yaml
evidence_hints:
  papers: [papers/kaplan2020, papers/hoffmann2022,
           papers/muennighoff2023, papers/sardana2023,
           papers/porian2024, papers/besiroglu2024]
```

**힌트 전달 경로 — 오해하기 쉬운 곳.** `--pack` 없이 돌리면 jail 의 힌트 파일은
`materialize_hints` 가 `hint_strings`(=`evidence_hints[kind]`)에서 **생성**한다
(`cycle.py:56-59`). `_workspace/*/papers.txt` 는 `--pack` 으로 넘기지 않는 한
**전혀 쓰이지 않는다.** 그 파일을 고쳐도 아무 효과가 없다.

힌트는 논문 본문이 아니라 **식별자 문자열**뿐이고, 런타임의 학습 지식에 의존한다.
live6 이 그 방식으로 충분함을 보였다(아래). 요약 본문을 사람이 써 넣으면
**그 사람이 근거 코퍼스의 저자가 되므로** 하지 않는 편이 낫다.

### 효과 (인간 리뷰 전, 기계 관측만)

- **후속 문헌 인용**: generate 근거 18건 중 **신규 4편이 12건**
  (porian 4 / muennighoff 3 / besiroglu 3 / sardana 2), kaplan2020 은 1건으로 떨어졌다.
  9문항 중 8문항이 후속 문헌에 근거한다.
- **질문의 성격이 바뀌었다.** live5b 는 두 논문 *사이의 갭*을 팠고 6건이
  "이미 답이 나옴"으로 거부됐다. live6 은 후속 문헌이 **끝난 지점에서 시작**한다 —
  Muennighoff 의 4-epoch knee 를 놓고 *왜* 생기는지(Q-0016), Porian 의 분해 후
  *잔차가 남는지*(Q-0017), Sardana 의 처방이 수요 *불확실성* 하에서도 서는지(Q-0018).
- **측정 가능한 변수로 이동**. live5b 의 이름뿐인 변수 3건
  (`irreversible_entropy_production_rate` 등) 같은 것이 사라지고,
  프로파일러·실행 로그·공개 데이터 재분석으로 잴 수 있는 변수가 자리했다.

### 남은 패턴 두 가지

- **`OP-XDOM` 은 계속 외부 도메인 유비를 부른다.** 상전이(live3c) → 재규격화군(live4b)
  → 비평형 열역학(live5b) → 제어이론 외란 제거(live6, Q-0011). 네 번 연속이다.
  live6 것은 두 논문에 근거하고 기제를 특정한다는 점에서 이전보다 낫지만,
  이 연산자가 유비를 부르는 구조인지 확인이 필요하다.
- **자원 초과 설계가 재발했다.** Q-0010 은 `1e25 FLOPs` 영역을 요구한다.
  live5b Q-0001 이 `1e18~1e22` 실측 스윕으로 실행 가능성 게이트에서 탈락했는데
  더 큰 규모를 요구한다. 회피 창에 그 사유가 실려 있었는데도 재발했다.

### 인간 리뷰 결과와 리뷰어 관측 (2026-08-20)

`adopt 3 / reject 5 / defer 1`. **live5b 의 9/9 거부에서 실질 개선**이고
live3c 이후 첫 채택이다. 코퍼스 수리의 효과는 인간 판정으로 확인됐다.

거부 사유의 **유형이 바뀐 것**이 더 중요하다. live5b 는 6건이 "이미 답이 나옴"이었는데
live6 에는 그 유형이 **0건**이다. 대신 실행 가능성(3건)과 전제 오류(2건)로 옮겨갔다.

리뷰어 관측 2건:

**(1) 근거 오귀속이 형식 게이트를 통과한다.** Q-0012 의 besiroglu2024 인용은 원 논문
범위와 불일치, Q-0010 의 porian2024 인용도 과잉 확장으로 의심된다. 코드로 확인했다 —
`G-GROUND` 는 `e["source"]` 가 힌트와 부분 일치하고 `e["claim"]` 이 **비어 있지 않은지만**
본다(`gates.py:18-24`). 주장이 그 논문의 실제 내용인지 검사하는 코드는 없다.

**이것은 게이트를 강화해서 고칠 수 없다.** 힌트가 식별자 문자열뿐이라 기계에는
대조할 원문이 없다. 실질적 선택지는 (a) `--pack` 으로 논문 본문을 코퍼스에 넣기,
(b) contrarian 에게 인용 충실도 공격을 명시적으로 시키기(`DISSENT_TYPES` 에 `evidence`
가 이미 있다) 둘 중 하나다.

**(2) 생성기가 비공개 프론티어 데이터를 실행 계획의 입력으로 가정한다.** 거부 5건 중
3건(Q-0010 10^24–10^26 FLOPs 그리드, Q-0014 비공개 사고 로그)과 유보 1건이 실행 가능성에서
걸렸다. **회피 신호로는 막히지 않았다** — live5b Q-0001 이 `1e18~1e22` 스윕으로 탈락했고
그 사유가 회피 창에 실려 있었는데도 live6 은 더 큰 규모를 요구했다.
리뷰어 권고는 "공개 획득 가능한 데이터·재현 가능한 규모만 실행 계획에 사용" 을
**상시 제약**으로 거는 것이다. 그 자리가 브리프의 `constraints` 인데, 아래대로 죽어 있다.

### 죽은 브리프 필드 (live6 조사 중 확인)

생성기에 실제로 도달하는 것은 `allocation_slice` 안의 것뿐이다
(`operators`, `evidence_kind`, `objective`, `avoid_patterns`, `hint_strings`,
`max_seeds`, `must_consider`). 그 밖에:

- **`constraints`** — `schema.py:142` 에 정의만 있고 **어디서도 읽지 않는다.** 죽은 필드.
- **`forbidden_premises`** — contrarian/judge 에만 전달되고(`cycle.py:153,262`)
  **generate 에는 도달하지 않는다.**

브리프 작성자가 이 둘로 생성을 제어할 수 있다고 착각하기 쉽다.
`EXCLUDE_FAMILIES` 가 선언만 되고 강제되지 않던 것과 같은 유형이다. 아직 고치지 않았다.

## 7.9 인프라 실패를 품질 판정으로 바꾸지 않기 (2026-08-20~21)

`RUN-20260820-live7b` 는 판정 중 GLM 크레딧이 소진되어 judge 하나가 타임아웃됐다.
`compose` 는 판정 카드 부재를 판정자가 내린 `GATE_FAIL` 과 같이 취급했으므로
**멀쩡한 질문 4건이 `REJECTED` 로 확정됐다.** 인프라 실패가 품질 판정의 옷을 입은 것이다.

- `missing_card` 는 이제 판정자의 `GATE_FAIL` 과 분리되어 **`DORMANT`** 로 간다(커밋 `a6ef95b`).
  `DORMANT → SCORED` 가 합법이라 회수 가능하다. 판정자가 실제로 낸 `GATE_FAIL` 과
  기계 게이트 실패는 그대로 `REJECTED` 다 — 그것은 질문에 대한 실제 증거다.
- `report` 에 **`unjudged`** 추가. 이런 런에서도 `protocol_valid` 는 참으로 남는다
  (프로토콜은 지켜졌고 런타임이 죽었을 뿐이다). 그래서 이 필드가 없으면
  3분의 1을 잃은 런이 헤드라인만으로는 멀쩡해 보인다. `slo_scored_ge_8` 만이 신호였다.
- live7b 의 4건(Q-0019/0021/0022/0024)은 `REJECTED → DORMANT` 로 복구했다.
  복구 전에 **기계 게이트 통과 + 점수 없음**을 확인했다 — 카드 부재로 죽었다는 서명이다.

### 파생 결함 — `DORMANT` 는 판정 대기가 아니다 (커밋 `c4a4d63`)

`open_review` 가 `DORMANT` 질문을 `pending` 판정 카드로 올리는데
**`DORMANT → REVIEWED` 는 불법 전이**라, 그런 질문을 가진 런은 마감이 불가능해진다.
위 변경 이전에도 `normative`/`meta` 질문이 반론에서 상처를 입으면 같은 경로로 깨졌다 —
잠재 결함이었고 위 변경이 흔한 경로로 만들었다.

`DORMANT` 는 **보류**다. 판정받은 적 없는 질문의 다음 단계는 재판정이고,
클래스가 범위 밖인 질문은 인간이 정할 것이 없다. 판정 카드에서 빼되
`dissent_portfolio` 에는 남긴다 — `preflight_close` 가 실제로 요구하는 것은 그쪽이다.

### 리뷰 자료 생성 시 주의 — 벤더는 런의 `allocation.yaml` 에서 읽어라

슬롯 번호는 재사용된다. GLM 은퇴 후 Grok 이 LWAR3 을 받았으므로,
**현재 레지스트리로 과거 런의 벤더를 표기하면 틀린다** (live7b 의 `zai` 산출물이
`xai` 로 찍혔다). 런 디렉터리의 `allocation.yaml` 이 당시 슬롯별 `vendor_family` 를
기록하고 있으니 그것이 정답이다.

## 7.10 `--pao` 경로에는 중복 억제가 없다 (2026-08-21, live8에서 실측)

> **⚠ 아래 "유사도 1.00 이 3건" 은 절 안에서 1건으로 정정된다.** 나머지 2건은 판정을 받은 적
> 없는 `DORMANT` 재질문이라 정당했다. 절 끝의 "정정" 소절까지 읽을 것.


live8 은 live7b 와 **완전히 같은 브리프**로 돌렸다(제약 3건 + 코퍼스 6편).
바뀐 것은 LWAR3 벤더뿐이다(`zai` → `xai`, 크레딧 소진이 강제한 교체).

연산자 슬롯별 자카드 유사도(live7b vs live8, `token_set` 기준):

| LWAR | 연산자 | 유사도 |
|---|---|---:|
| LWAR1 openai | OP-BOUND / OP-CONTRA / OP-INVERT | 0.15 / 0.25 / 0.50 |
| **LWAR2 google** | **OP-MISSVAR / OP-SCALE / OP-XDOM** | **1.00 / 1.00 / 1.00** |
| LWAR3 xai(신규) | OP-CAUSAL / OP-CF / OP-MEASURE | 0.15 / 0.04 / 0.09 |

**Antigravity 가 세 문항을 토큰 집합까지 동일하게 재생성했다.** 비슷한 것이 아니라 같다.

원인은 둘이고 둘 다 우리 쪽이다.

**(1) 생성기 입력이 완전히 동일했다.** live7b 를 마감하지 않아 회피 창이 그대로였고,
브리프·제약·힌트도 같다. 결정적으로 `build_allocation` 은 `operators` 를
**인덱스 순서로** 배정하므로 로스터 순서가 같으면 매 런 같은 연산자가 같은 슬롯에 간다.
즉 결정적 런타임에게는 같은 입력이 주어졌고, 같은 답이 나온 것은 런타임의 결함이 아니다.

**(2) 정규 경로에 중복 억제가 없다.** `prior_sets_for` / `diversity_ok` 는
`explore_loop`(로컬 경로)에서만 호출된다. **`explore_loop_pao` 는 발행하고 받아서 그대로 쓴다**
(`cycle.py:253-269`). live1 이후 모든 라이브 런이 이 경로였으므로,
**중복 억제는 이 저장소에서 한 번도 작동한 적이 없다.**

`inject_divergence` 도 있으나 런 **내부** 재시도용이고 런 **사이**에는 적용되지 않는다.

부수 주의: `prior_sets_for` 는 `SCORED`/`ADOPTED` 만 읽는다. §7.9 에서 판정 못 받은 질문을
`DORMANT` 로 옮겼으므로 그것들은 억제 대상에서 빠진다 — PAO 경로에서는 애초에 호출되지
않으니 지금은 무해하지만, 억제를 켤 때 함께 결정해야 한다.

### 정정 — 반복은 3건이 아니라 1건이다

`prior_sets_for` 는 `SCORED`/`ADOPTED` 만 읽는다. live7b 의 OP-SCALE(Q-0019)과
OP-MISSVAR(Q-0021)은 §7.9 에서 `DORMANT` 로 복구한 것들이라 선행 집합에 없다.
**판정을 받은 적 없으므로 다시 묻는 것이 정당하고, live8 에서 실제로 판정을 받았다**(9/9 scored).
텍스트가 같아도 그 2건은 낭비가 아니라 회수다. 진짜 반복은 OP-XDOM 1건뿐이다.

### 수정 (커밋 `3d325e2`)

**(a) 연산자를 런마다 회전.** `build_allocation` 이 `brief_id` 의 안정 다이제스트로
오프셋을 만들어 `default_ops_for(i, k, offset)` 에 넘긴다. 전 슬롯이 같은 양만큼
이동하므로 삼중조는 여전히 서로소이고 이종성 키도 유지된다. `brief_id` 가 없으면
오프셋 0 이라 기존 동작 그대로다. 오프셋 공간은 12 이므로 **연속 두 런이 충돌할 확률이
1/12 있다** — 그래서 (b)가 필요하다.

**(b) 반복 기록.** `explore_loop_pao` 가 `note_repeats` 로 각 seed 의 선행 최대 자카드를
재고 `TH_PAIR`(0.55)를 넘으면 `report.repeat_seeds` 에 남긴다. **버리지 않고 기록만 한다** —
반복은 형식 오류가 아니고, 버리면 런이 자기 프로토콜 검사 아래로 줄어들며,
반복의 가치는 검토자가 판단할 몫이다.

### 제약(§7.8 `constraints`)의 효과는 재현됐다

- **자원 초과 설계 0건** — live7b 에 이어 9/9. 전부 공개 데이터 또는 재현 가능한
  20M~300M 그리드. 프론티어 규모 신규 학습이나 비공개 로그를 전제하는 질문이 없다.
- **기각 조건 9/9 등가 마진** — 점등식 없음.
- 계측학 군집은 5/9 → 3/9 로 줄었으나, **그 3건이 전부 LWAR2 의 복제본**이다.
  줄어든 것이 아니라 LWAR1·LWAR3 이 새 질문을 낸 덕이다.

## 7.11 `review` 역할 — 추천은 하되 결정은 못 한다 (2026-08-21)

> **⚠ 이 절이 세운 "자원 재고를 리뷰어에게 주면 일치율이 오른다" 가설은 반증됐고,
> 계획 자체가 §7.12 에서 철회됐다.** 리뷰어는 우리 자원을 몰라야 한다.


Fable 5 를 **LWAR4(anthropic)** 로 붙여 리뷰어로 쓴다. 생성 로스터(LWAR1/2/3)에는
넣지 않으며, `request_review` 가 **런의 일부라도 생성한 LWAR 의 리뷰를 거부**한다.

### 가드는 관행이 아니라 코드에 있다

`assert_transition` 은 `ADOPTED` 에 `actor="human"` 을 요구하지만 `close_review` 가
그것을 무조건 넘긴다 — 즉 **`review.yaml` 을 채우는 쪽이 정직하다는 가정**이었다.
리뷰어 LWAR 을 붙이면 그 가정이 하중을 받으므로, 가드를 강제 가능한 곳으로 옮겼다:

- `apply_recommendation` 은 모든 판정과 사유를 채우되 **`reviewer` 를 비워 둔다**
- `preflight_close` 가 `reviewer` 없는 런을 거부한다 → **사람이 `ratify` 하기 전에는 마감 불가**
- 이 보장은 **리뷰어의 정직성에 의존하지 않는다** (`tests/if/test_review_role.py`)

되먹임 추적: `review.yaml` 의 `reviewer_kind`/`recommended_by`,
`decisions.jsonl` 각 행의 `decided_by`, `report.yaml` 의 `reviewer_kind`.
거부 사유는 다음 런의 `avoid_patterns` 가 되므로 **기계가 쓴 것과 사람이 쓴 것이
사후에 구별되어야 한다.**

리뷰어 패킷은 **출처가 없다** — 벤더·연산자·기계 점수 없음. `open_review` 가 이미
그것들을 `review.yaml` 에 못 넣게 하는 것과 같은 이유다. 반론은 판정 결과와 함께 넣는다:
이미 적중한 공격은 저자가 아니라 질문에 대한 증거다.

### 검증 — live6 재판정, 일치 7/9

정욱님이 이미 판정한 live6 을 `--no-apply` 로 Fable 에게 다시 물었다
(패킷에 선행 판정·사유는 들어가지 않는다. 확인함).

| QID | 사람 | Fable |
|---|---|---|
| 0010 0011 0012 0014 | reject | reject |
| 0015 0016 0017 | adopt | adopt |
| **0013** | **defer** | **adopt** |
| **0018** | **reject** | **defer** |

**문헌 대조는 완전히 일치했다.** "이미 답이 나옴"(Muennighoff/Sardana/Porian) 계열 3건과
전제 오류 2건 모두 같은 판정이 나왔다.

불일치 2건의 성격이 다르다:

- **0013 은 자원 상대성이다.** 사람은 *"클러스터 접근권이 확인되면 재판정"*,
  Fable 은 *"접근 가능한 규모의 프로파일링으로 실행 가능"*. **Fable 은 우리 자원을 모른다.**
  live6 브리프에는 `constraints` 가 없었고(§7.8 은 live7 부터), 패킷에도 넣지 않았다.
  **이것은 Fable 의 실패가 아니라 패킷의 누락이다.**
- **0018 은 사실상 같은 진단이다.** 사람은 *"손실함수·위험태도를 명시적으로 도입해야
  비자명해진다"*, Fable 은 *"목적함수를 사전 등록으로 고정해 재정식화 후 재상정"*.
  **결함을 같이 봤고 처분만 갈렸다**(버릴 것인가 고쳐 쓸 것인가).

경향: Fable 은 두 건 모두 **한 칸씩 관대**하다(reject→defer, defer→adopt).
채택률만 보고 위임하면 이 편향이 누적된다.

### 재측정 — 제약을 실어도 7/9 그대로다 (가설 반증)

§7.11 의 불일치 2건 중 0013 이 자원 정보 부재 때문이라 보고, 패킷에 `constraints`
3건(live8 브리프)을 실어 `--no-apply` 로 재리뷰했다(round 1).

**결과: 7/9 → 7/9. 판정이 하나도 움직이지 않았다.**

제약이 무시된 것이 **아니다.** Fable 의 v2 사유는 *"세 제약을 모두 통과한다"* 로 시작해
셋을 하나씩 검토하며, **9건 전부 사유가 새로 쓰였다**(v1 과 동일한 사유 0건).
읽고 반영했는데 결론이 같았다.

**진단: `constraints` 는 잘못된 도구다.**

- `constraints` 는 **규칙**이다 — "공개 획득 가능한 데이터와 재현 가능한 규모만".
  Fable 은 다중 노드 분산 학습 프로파일링이 *"접근 가능한 규모에서 공개 재현 가능"* 하다고
  읽었고, 일반론으로는 타당한 독해다.
- 사람의 유보는 **사실**에 관한 것이었다 — *"클러스터 접근권이 확인되면 재판정"*.
  **우리가 그 클러스터를 가지고 있는가**는 규칙이 아니라 재고 목록이다.

규칙은 재고를 대신할 수 없다. "재현 가능한 규모만 써라" 는 우리가 노드를 8대 가졌는지
0대 가졌는지 말해 주지 않는다. 이 정보는 **운영자만 안다.**

### 부수 소득 — 재현성

사유가 9/9 새로 쓰였는데 **판정은 9/9 동일**했다. 두 번의 독립 실행에서 같은 결론에
서로 다른 논증으로 도달한 것이므로, Fable 의 판정은 잡음이 아니다.
불일치 2건도 안정적이다(둘 다 사람보다 한 칸 관대).

### 또 하나 고친 것 — 재리뷰가 구조적으로 불가능했다

`task_id` 가 `(run_id, role, lwar, round_n)` 에서 결정적으로 나오는데 `round_n` 을
0 으로 고정해 두어, 같은 런의 두 번째 리뷰가 원장에 막혔다
(`task already has a ledger entry`). 자동으로 다음 빈 라운드를 쓰도록 고쳤다.
재리뷰는 정상적인 요구다 — 자원 범위가 바뀌거나 2차 의견이 필요할 때.

## 7.12 IF 는 자기 예산을 몰라야 한다 (2026-08-21)

**IF 의 목적은 질문 생산이다. 그 질문이 이 시스템에서 실행 가능한지는 독립적이어야 한다.**
§7.8 의 `constraints` 는 이 선을 넘었고, 그 뒤 리뷰어에게까지 확장하려던 것을 철회했다.

### 실행 가능성에는 두 가지가 섞여 있다

- **(A) 누구도 못 하는 것 — 질문의 결함.** 반증 조건이 비공개 소유 데이터로만 판정되고
  공개 대체물이 없으면, 그것은 검정이 아니라 소망이다. 게이트로 거르는 것이 맞다.
- **(B) 우리가 못 하는 것 — 우리의 사정.** 다중 노드 클러스터가 없다는 것은
  질문의 속성이 아니다. **`DEFERRED` 가 이미 이 자리다**(`DEFERRED → SCORED` 로 복귀 가능).

### 오염의 증거

`constraints` 는 브리프에 있으므로 **생성기에 전달된다.** 즉 (B)가 어떤 질문이 태어나는지를
결정하고 있었다. 같은 `OP-SCALE` 슬롯의 변화:

| 런 | 질문 |
|---|---|
| live6 (제약 없음) | Post-Chinchilla **>10^25 FLOPs** 영역에서 배치 확장·불안정성이 Chinchilla 비율을 파괴하는가 |
| live8 (예산 제약) | **소형 재현 가능 스케일 10^18~10^20** 에서 Huber vs MSE 피팅 민감도 |

**질문이 우리 예산에 맞춰 스스로 축소됐다.** 세상에 관한 질문이 우리 계산서에 관한 질문이 됐다.
계측학 군집(live7b 9건 중 5건이 "회계를 바꾸면 지수가 불변인가")도 같은 현상이다 —
재분석은 언제나 실행 가능하므로 제약 하에서 가장 안전한 선택지다.

### 조치 — live9 브리프

예산 조항을 제거하고, 남긴 셋은 모두 질문 자체의 속성이다:

1. 반증 조건이 **원리적으로** 도달 가능할 것. **"규모나 비용의 크기 자체는 결함이 아니다"** 를
   명시했다 — 금지를 빼는 것만으로는 축소 압력이 돌아오지 않는다.
2. 변수가 조작적으로 정의될 것. **새 측정 절차를 정의하는 것은 허용**한다
   (구 조항 "기존 문헌에 측정 절차가 확립된 것만" 은 과잉이었다. 근거였던 live5b 거부 3건은
   전부 *미정의* 를 지적했지 *어렵다* 를 지적하지 않았다).
3. 기각 조건은 등가 마진을 가진 연속량. 점등식은 **누구에게도** 판정 불가다.

리뷰어에게 자원 재고를 주려던 계획은 철회했다. **Fable 은 우리 자원을 모르는 채로
질문의 품질만 판정하고, `adopt` 중 지금 못 할 것을 사람이 `defer` 로 내린다.**
live6 Q-0013 의 불일치(사람 defer / Fable adopt)는 결함이 아니라 이 분담이 작동한 모습이었다.

### 측정 실패 — 자기 실험을 자기가 방해했다

핵심 지표로 삼은 `OP-SCALE` 이 live9 에 배정되지 않았다. §7.10 의 연산자 회전이
`brief_id` 로 오프셋을 돌리기 때문이다. **회전과 제약 제거를 같은 런에 넣은 것이 잘못이다** —
live4b 에서 "교란 변수가 셋" 이라고 경고해 놓고 같은 실수를 반복했다.

부수 소득은 있다: **`OP-2ND` / `OP-REGIME` / `OP-ADV` 가 처음 등장**했다. 회전이 의도대로
질문 공간을 넓히고 있다.

### 남은 통로 — 회피 창

`constraints` 를 지워도 되먹임이 예산 압력을 우회로로 나른다. live9 회피 창 8건 중 2건:

- *"비공개 소유 데이터다. 공개 대체 자료가 없다"* — **(A), 정당**
- *"10^24–10^26 그리드는 격자점 하나가 수천만 달러급이라 프론티어 연구소 외부에서 실행 불가.
  해당 내부 로그도 비공개"* — **(A)와 (B)가 한 문장에 섞여 있다**

`query_avoid_patterns` 는 사유 텍스트를 그대로 나르며 둘을 구별하지 않는다.
판정 시 `reason_kind`(`question_defect` / `our_capacity`)를 붙이고 전자만 회피 창에
싣는 것이 해법이지만, 위 한 건은 운영자가 쓴 문장이라 **분류를 임의로 하지 않는다.**

## 7.13 상시 위임 — 채택 판정은 Fable 5 가 한다 (2026-08-21, 운영자 결정)

**운영자 결정**: *"앞으로 질문에 대한 채택에 대한 나의 선택은 Fable 5의 선택으로 대신한다."*

live6 재판정에서 일치 7/9, 사유를 9/9 새로 쓰고도 판정은 9/9 동일(재현성 확인),
문헌 대조는 완전 일치했다(§7.11). 불일치 2건은 자원 상대성 1건과 같은 진단·다른 처분 1건이었다.

### 기록은 사실대로 남는다

`REVIEWER_KINDS` 에 **`delegated`** 를 추가했다. 셋을 구별한다:

- `human_ratified` — 사람이 이 판정들을 **읽고** 서명했다
- `delegated` — 사람이 **상시 위임을 승인**했고 기계가 이 건을 판정했다. 책임은 사람에게 있으나 읽지는 않았다
- `human` — 사람이 직접 판정표를 채웠다

둘을 같이 기록하면 **어느 판정을 사람이 실제로 봤는지**가 사라진다. 이 사유들이 다음 런의
`avoid_patterns` 가 되므로, 질문 품질이 흔들릴 때 **위임 종결과 상관되는지**부터 물어야 한다.

`ratify --delegated` 가 이 경로이고, `close_review` 가 `decided_by: delegated` 로 각 행에 남긴다.

### 첫 적용 — 3개 런 23문항 (2026-08-21)

| 런 | adopt | reject | reviewer_kind |
|---|---:|---:|---|
| live7b | 2 | 3 | delegated |
| live8 | 3 | 6 | delegated |
| live9 | 5 | 4 | delegated |

`decisions.jsonl` 23행 전부 `decided_by: delegated`, `reason_kind: question_defect`.
질문 상태: ADOPTED 10 / REJECTED 13 / DORMANT 4(live7b 미판정분, 재판정 대상).

**회피 창이 처음으로 완전히 교체됐다** — 8건 전부 live7b~live9 의 `question_defect` 사유다.
live5b·live6 의 낡은 신호가 빠졌고, 예산 사유(§7.12 의 혼재 1건 포함)도 함께 밀려났다.

### 위임되지 않는 것

`our_capacity` 판정은 구조적으로 Fable 이 내릴 수 없다 — 우리 자원을 모르기 때문이다(§7.12).
따라서 **`ADOPTED` 는 "추구할 가치가 있다" 이지 "지금 실행한다" 가 아니다.**
지금 못 할 것을 `DEFERRED` 로 내리는 판단은 운영자에게 남아 있으며, 하지 않아도 무해하다 —
채택 목록에 당장 못 하는 질문이 섞일 뿐, 질문의 가치 판정은 오염되지 않는다.

## 7.14 회피 창이 브리프를 대신해 오염을 나른다 (2026-08-22, live10g)

§7.12 의 측정을 다시 세웠다. 연산자 회전이 `brief_id` 의 결정적 해시라는 점을 역이용해,
**live8 과 배정이 완전히 같아지는 `brief_id`(`RUN-20260822-live10g`)** 를 골랐다 —
LWAR2(google) 가 `[OP-SCALE, OP-XDOM, OP-MISSVAR]` 를 받는다.
`domain`·`goal`·`evidence_hints`·`budget`·`mode` 는 live8 과 동일하고,
**다른 것은 `constraints` 내용뿐인 통제된 비교**다.

### 결과 — 가설 반증

| 런 | `constraints` | OP-SCALE 질문 |
|---|---|---|
| live6 | 없음 | **>10^25 FLOPs**, Post-Chinchilla 불안정성 |
| live8 | 예산 조항 | 소형 재현 가능 **10^18~10^20**, Huber vs MSE 민감도 |
| live10g | 예산 조항 **제거** | 소형 재현 가능 **10^18~10^20**, Huber 피팅 b 의 SE 단조 증가 |

**예산 조항을 빼도 규모가 돌아오지 않았다.** §7.12 의 진단(브리프 `constraints` 가 축소를
일으켰다)은 이 런에서 지지되지 않는다.

### 오염원이 이동했다

`constraints` 에는 규모 어휘가 없다(`재현 가능` 없음, `소형` 없음, `10^1` 없음).
**`avoid_patterns` 에 있다**(`재현 가능`·`1e1`·`FLOPs` 모두 있음). 두 사유가 나른다:

- *"질문이 스스로 답을 결정해 두었다 — **공개 실험 규모(C 1e18~1e21)** 에서…"*
  거부 사유가 **부수적으로 언급한 규모 범위**를 생성기가 작업 범위로 흡수한다.
- **`reason_kind` 로는 막을 수 없다.** 그 사유는 정당한 `question_defect` 이고
  규모는 곁다리로 나온 것이다. (A)/(B) 축은 사유의 **판정 근거**를 가르지
  **사유가 흘리는 부수 정보**를 가르지 못한다.

**즉 브리프를 정리해도 되먹임 고리가 같은 압력을 계속 전달한다.** §7.12 는 통로 하나를
막았을 뿐이고, 회피 창 자체가 남은 통로다.

### 부수 발견 — 회피 패턴은 억제만 하지 않고 **수리시킨다**

회피 창의 한 사유는 live7b Q-0019(거부된 `OP-SCALE`)의 것이다:
*"판정 구조가 자기모순이다 — 스케일 구간이 증가할 때 신뢰구간 확장을 묻는데
criterion 은 더 작은 서브그리드의 50% 확장을 성공으로 정의해 방향이…"*

live10g 의 `OP-SCALE` 질문은 **동일 표본 크기(N=50) 서브그리드**로 방향 모순을 없애고
**등가 마진(SE 차이 > 0.03)** 을 붙였다. **지적된 결함이 정확히 수리돼 돌아왔다.**
자카드 0.18 — 반복이 아니라 다른 질문이다.

지금까지 회피 패턴을 "피하라" 신호로만 봤는데, 실제로는 **"이렇게 고쳐서 다시 물어라"**
로도 작동한다. 좋고 나쁨을 단정하기 이르다 — 함정은 제거되지만 질문이 같은 이웃에 머문다.

### 방법론 교훈

**또 변수를 하나만 바꿨다고 생각했고 또 틀렸다.** live7b~live9 세 런을 닫으면서
**회피 창 8건이 통째로 교체된 것**을 계산에 넣지 않았다. 브리프를 고정해도
창이 바뀌면 생성기 입력은 바뀐다. 다음 비교 실험은 **창까지 고정**하거나,
최소한 창의 변화량을 함께 기록해야 한다.

## 7.15 회피 창 정책 — Fable 5 결정 (2026-08-22, 미구현)

운영자가 이 설계 결정을 Fable 5 에게 위임했다(*"Fable 5가 판단해서 정하게 지시하라"*).
결정 원문은 `_workspace/decisions/avoid-window/outbox/decision.md` 이나 **`_workspace` 는
git 제외**이므로 아래가 추적되는 기록이다. 제시한 문제는 §7.14 의 관측 3건이다.

### 결정 — 두 층으로 분리

**1층 · 패턴 등록부** (`.if/memory/avoid_registry.yaml`, `decisions.jsonl` 에서 재구축 가능한 파생 뷰)

- 리뷰어가 `question_defect` 거부마다 **한 줄 `pattern`** 을 추가로 쓴다.
  결함의 **구조만**, 수치·규모·자원·데이터셋 이름 금지.
- 같은 pattern 이 **서로 다른 2개 런 이상**에서 관측되면 등재.
- 퇴출은 밀려남이 아니라 **불용** — 최근 **4개 마감 런** 동안 새 인스턴스가 없으면 내린다.
  도메인당 상한 **12줄**.
- 리뷰 시점에 리뷰어에게 등록부를 보여주고, 같은 결함이면 그 줄을 재사용하게 한다.

**2층 · 원문 창** (수리 연료)

- 거부 사유 **전문** 유지. 선택 규칙만 `최근 8건` → **`최근 마감 런 3개 × 런당 최대 3건, 상한 9`**.
- 런 내 선택은 **등록부에 없는 pattern 의 사유 우선**(등록부가 이미 커버하는 원문은 중복).
- 두 층 모두 **전 슬롯에 전량** 배포(§7.10 의 부분 배포 재발 실측을 존중).

`query_avoid_patterns` 는 `{patterns: [...], recent_reasons: [...]}` 를 반환하고
`build_allocation` 이 두 블록을 모두 싣는다.

### 부수 정보 누출 — 읽기가 아니라 **쓰기 시점**에 막는다

- **읽기 시점 편집(redaction)은 하지 않는다.** 정당한 사유의 사후 훼손은 수리 신호를 망가뜨리고
  소급 재해석 금지 원칙과 충돌한다.
- 리뷰어 계약에 규율 추가: 결함 자체가 아닌 수치(규모·FLOPs·예산·하드웨어·코퍼스 크기)는
  값이 아니라 구조로 쓴다. *"공개 규모에서는 제약이 걸리지 않는다"* 라고 쓰고 *"1e18~1e21"* 은 쓰지 않는다.
- 기계 리뷰어에는 semantic 게이트에 **쓰기 린트**(수치+단위 탐지, 결함 자체인 수치는 명시 마커로 허용).
  **린트는 완화 장치이지 보증이 아니며 잔여 누출은 받아들인다.**

### 수리 효과 — 의도적으로 보존한다

수리는 실패 모드가 아니라 **이 되먹임 고리의 성공 모드**다. 연료는 사유 전문의 구체성이므로
2층 유지가 보존 장치이고, **1층만 남기고 원문을 없애는 설계는 채택하지 않는다.**
`repaired` 계측 추가: 직전 런의 같은 연산자 거부 질문과 유사도 <0.4 이고 해당 pattern 이
재발하지 않았으면 `repaired`.

### 포기하는 것 (Fable 명시)

리뷰어 부담 증가(인간에게는 강제 불가) · pattern 한 줄의 정보 손실 ·
파생 상태 파일 하나 추가 · 대량 거부 런의 사유 일부 미전달(13건 중 원문은 3건) ·
단위 없는 수사·고유명사를 통한 잔여 누출.

### 검증 방법 (Fable 명시 — 구현 후 반드시 실행할 것)

1. **지속성** — 다음 대량 거부 마감 직후 `allocation.yaml` 에 기존 등재 pattern 이 남아 있는가.
   기준: 물리 유비 수입·자원 초과 설계 두 함정이 창에서 사라지지 않아야 한다.
2. **재발률** — 등재 pattern 으로 거부되는 문항 수가 런당 감소해야 한다.
   4개 런 연속 줄지 않으면 등록부 전달 방식이 틀린 것이다.
3. **누출** — 브리프에 없고 창 원문에만 있는 수치·범위가 생성 질문에 등장하는 건수.
   감소해야 하고 0 이 목표. **린트 거부 로그가 0 이면 린트가 작동하지 않는 것**이므로 함께 본다.
4. **수리 보존** — `repaired` 건수가 유지되어야 한다. 0 으로 떨어지면 원문 창을 너무 줄인 것이고,
   첫 조정은 런당 3건 → 4~5건이다.

### Fable 이 확신하지 못한다고 밝힌 것

- **상수 4런 / 12줄 / 런당 3건은 실측 없는 초기값**이다. 방향에는 확신이 있으나 숫자는 검증 4항의 조정 대상.
- **pattern 어휘가 수렴할지 모른다.** 수렴하지 않으면 등록부가 비슷한 줄의 목록으로 퇴화하고,
  그때는 자유 문장이 아니라 **고정 분류표(taxonomy)** 로 바꾸는 후속 결정이 필요하다.
- **인간 리뷰어의 규율은 강제 수단이 없다.** 누출 검증이 악화되면 `decided_by` 로
  인간 사유인지 기계 사유인지 갈라 확인하라.

## 7.16 수리 고리는 예외가 아니라 지배적 양상이다 (2026-08-22, live10g 마감)

> **⚠ 이 절 끝의 "질문 공간이 수리본으로 수렴한다" 는 한 런에서 끌어낸 성급한 추세다.**
> live11 은 수리 4 / 반복 0 / **새 영역 5** 였다(§7.17). 수렴은 단조롭지 않다.


§7.15 를 구현하고 live10g 를 새 계약으로 마감했다. 결과: **`adopt 9 / reject 0`.**
이전 분포(2/5, 3/9, 5/9)와 크게 다르다.

degenerate 리뷰가 아니다. 사유가 360~450자로 구체적이고, 대부분이 이렇게 시작한다:

> *"이전 런에서 기각된 신뢰구간 확장 문항의 **수리본**으로, 치명 결함이었던 방향 자기모순이
> 고쳐졌고 표본 크기를 N=50으로 맞춰 점 수 교란도 통제에 들어왔다"*
> *"두 런에 걸쳐 기각된 어휘 크기 공변량 문항의 수리본이며, 기각 사유였던 식별 불가와
> 분석 단위 오류를 정확히 해소했다"*

**live10g 는 대부분이 이전 거부 질문의 수리본이었고, 리뷰어가 그것을 알아보고
지적됐던 결함이 실제로 고쳐졌는지 검증했다.** §7.14 에서 한 건으로 관측한 수리가
런 전체 규모로 재현된 것이다.

### 그래서 생긴 문제 — 새 계약이 한 번도 발동하지 않았다

`pattern` 은 **`question_defect` 거부에만** 요구되고, 쓰기 린트도 reject/defer 사유에만 걸린다.
**거부가 0건이면 새 기계장치 전체가 우회된다.** 등록부는 여전히 비어 있고(`patterns 0`),
린트 거부 로그도 0이며, Fable 이 검증 3항에서 *"린트 거부 로그가 0이면 린트가 작동하지 않는
것"* 이라 한 상태와 **구별되지 않는다.** 이번 마감은 계약의 실행 가능성조차 시험하지 못했다.

### 부수 관찰 — 조건부 채택을 담을 곳이 없다

Fable 은 채택마다 *"채택 조건 — 최소 3개 tier 로 확장할 것, …"* 을 붙였다. 스키마에
그 자리가 없어 **`reason` 본문에 섞여 들어간다.** 채택된 질문을 실제로 실행할 때
이 조건들이 어디에도 구조화돼 있지 않다.

### 해석 — 고리가 도는 것과 넓어지는 것은 다르다

수리가 작동한다는 것은 되먹임이 산다는 증거다. 그러나 **질문 공간이 이전 질문의 수리본으로
수렴하고 있다**는 뜻이기도 하다. Fable 이 §7.15 에서 *"함정은 제거되지만 질문이 같은 이웃에
머문다"* 고 한 긴장이 여기서 관측된다. 채택률이 올라간 것을 성공으로만 읽으면 안 된다.

## 7.17 새 계약이 처음 발동했다 — live11 (2026-08-22)

`repaired_seeds` 가 계측된 첫 런이자, `pattern` 필수화와 쓰기 린트가 실제로 걸린 첫 마감이다.

| | live11 |
|---|---:|
| 수리본(`repaired_seeds`) | 4 |
| 반복(`repeat_seeds`) | 0 |
| 이전 거부와 겹침 없음 | 5 |
| 판정 | `adopt 6 / reject 2 / defer 1` |

**§7.16 의 수렴 우려는 완화된다.** 절반 이상이 새 영역이고, `OP-SCALE` 은 거부됐던
신뢰구간 폭 질문 대신 데이터 제약 영역(*"Chinchilla 처방 고유 토큰의 1000분의 1"*)으로 갔다.

### 거부 2건 모두 `pattern` 을 달고 왔다

> *"이미 채택된 문항의 부분 분석을 독립 문항으로 재제출했고, 결합 모형이 구성상 함의하는 부호를…"*
> *"반사실이 고정하는 변수가 관측된 차이의 주원인이 아니어서 어느 결과가 나와도 가설을 판별하지…"*

**둘 다 수치가 없다.** 결함의 구조만 서술한다 — 쓰기 규율이 지켜졌고 린트가 막을 것이 없었다.
`decisions.jsonl` 에 `pattern` 보유 레코드가 처음 2행 생겼다(둘 다 live11).

### 등록부는 아직 비어 있다 — 정상이다

`patterns 0건`. 등재 조건이 **서로 다른 2개 런**이므로 live11 한 번으로는 오르지 않는다.
같은 pattern 이 다음 런에서 다시 관측돼야 첫 항목이 등재된다.
**Fable 의 검증 1·2항은 그때부터 측정 가능하다.**

### `repaired` 지표의 한계 — 두 숫자를 같은 축에서 읽지 말 것

`repaired_seeds` 는 *"같은 연산자의 가장 최근 거부 질문과 0 < 유사도 < TH_REPAIR"* 라는
**토큰 겹침 대리 지표**다. live10g 에서 Fable 이 *"수리본"* 이라 판정한 9건은 **질문을 이해한
결과**이고 같은 방식으로 잰 것이 아니다. **비교 기준선은 live11 부터**다.

## 7.18 pattern 어휘는 수렴하지 않았다 — Fable 이 예측한 그대로 (2026-08-22, live12)

live11·live12 두 런에서 `pattern` 5건이 기록됐다. **등록부 등재는 0건이다.**

| 런 | pattern |
|---|---|
| live11 | 이미 채택된 문항의 **부분 분석을 독립 문항으로 재제출**했고, 결합 모형이 구성상 함의하는 부호를… |
| live12 | 직전 런에서 채택 권고된 문항과 **동일 구조 설계의 재제출** |

**같은 결함이다.** 이미 채택된 질문을 다시 낸 것. 그런데 문장이 다르므로 **문자열 일치 키로는
같은 pattern 이 아니다.** 등재 조건(서로 다른 2개 런에서 같은 pattern)이 영원히 성립하지 않는다.

Fable 이 §7.15 에서 *확신하지 못한다*고 밝힌 셋 중 하나가 이것이다:

> *"pattern 어휘가 수렴할지 모른다. 수렴하지 않으면 등록부는 비슷한 줄의 목록으로 퇴화하고,
> 그때는 pattern 을 자유 문장이 아니라 **고정 분류표(taxonomy)** 로 바꾸는 후속 결정이 필요하다."*

리뷰어에게 등록부를 보여 재사용을 유도하는 장치는 **등록부가 비어 있으면 작동하지 않는다** —
보여줄 것이 없다. 초기 부트스트랩 구멍이다.

### 부수 관측 — 리뷰어가 근거 오귀속을 잡았다

live12 거부 사유 하나에 *"인용 주장에 **원 논문에 없는 내용이 섞인 근거 오귀속**"* 이 있다.
§7.11 에서 `G-GROUND` 가 인용의 **존재**만 보고 **내용 정합성**은 못 본다고 기록한 그 구멍을,
리뷰어가 실제로 메우고 있다. 기계 게이트로는 못 잡는 것을 모델이 잡는다.

### live12 요약

`adopt 4 / reject 5`. `repaired_seeds` **5**(live11 4) — Fable 검증 4항의 "유지" 조건 충족.
`repeat_seeds` 0. **`G-GROUND` 실패 2건** — 생성기가 코퍼스 밖 문헌(`carlini2019`,
`loshchilov2019`)을 인용하려 했다. **`scaling` 6편이 소진됐다는 직접 증거**다.

## 8. 다음 작업 (우선순위)

1. **다음 IF 런** — 브리프는 `_workspace/if-live9/brief.yaml` 을 본떠 `brief_id` 만 바꾼다.
   예산 조항을 다시 넣지 말 것(§0). 런 → `review-run`(LWAR4) → `ratify --delegated` → `close`.
2. **회피 창 정책** — `n=8` 고정이라 대량 거부 한 번에 축적 신호가 통째로 교체된다(§7.7, §7.13).
   창 확대, 도메인별 분리, 함정 유형 요약 유지 중 택일이 필요하다. 아직 결정되지 않았다.
3. **`OP-SCALE` 오염 제거 확인** — §7.12 의 측정이 실패했다. 연산자 회전이 `brief_id` 로
   오프셋을 돌리므로, `OP-SCALE` 이 배정되는 `brief_id` 를 골라야 비교가 선다.
   **변경을 한 번에 하나씩만 넣을 것** — 회전과 제약 제거를 같이 넣어 실험이 깨졌다.
4. **live2 `review.yaml`** — 아직 열려 있다. 위임 경로로 처리 가능하다.
5. 백로그: U11 D20 강제, U18 IfPhase2Roles — 아직 하지 않음.

OA `sanitize-idle`(work/·죽은 pid 청소)은 **미구현**. 전권 wipe 금지.

---

## 9. 하지 말 것

- `var/identities/` 스캔 후 남의 identity 채택 — **문서에 적힌 경로도 trusted handoff가 아니다**
- 유효 슬롯에서 재등록
- `.pao` / registry / lease / writer_lease 손편집
- OA가 벤더 CLI에 직접 지시 붙여넣기
- `lwar3_adp_loop.py` / `if_autorun.py`로 일반 PAO 태스크 처리
- live1 동결 해제, Qwen 재투입
- **ADOPTED 를 사람의 위임 없이 기계가 부여** — 상시 위임은 §7.13 에서 운영자가 승인했다.
  위임 경로는 `ratify --delegated` 뿐이고, `reviewer` 를 코드가 임의로 채우지 않는다
- **슬롯 번호로 런타임을 식별** — 번호는 재사용된다. LWAR3 은 xai → zai → xai 로 바뀌었다.
  과거 런의 벤더는 그 런의 `allocation.yaml` 에서 읽어라(§7.9)
- **은퇴 전에 `collect --archive` 를 건너뛰기** — 배달된 결과가 `outgoing/` 에 남아
  멀쩡한 슬롯이 `active_mailbox_work` 로 거부된다(§7.6, 은퇴 런북)

---

## 10. 다음 세션 부트스트랩

```text
1. HANDOFF §0 (지금 유효한 정책) + §1-§6 (현재 상태) + AGENTS.md + CLAUDE.md
   §7 은 사고 기록이다. 처음부터 읽지 말고, 필요한 절만 §0 의 참조를 따라간다.
2. 역할 OA → pao-oa SKILL.md
3. PAO_OA_ID mint(또는 직전 id 재사용) → presence → reconcile → status
4. 스킬 작업이면 .pgf/DESIGN-PaoLwarV118.md 가 권위 (P1-P6 done)
5. IF 작업이면 .pgf/DESIGN-InquiryFoundry.md 가 권위
```

**IF 런을 돌리기 전 확인:** `oa.py status --busy-grace 960` 으로 `alive_count >= 3`,
`needs_operator` 가 비어 있을 것. LWAR4(리뷰어)는 생성 로스터에 넣지 않는다.
