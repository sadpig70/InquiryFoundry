# HANDOFF — InquiryFoundry

세션 종료 시점: 2026-08-18 (OA = Claude Opus 5, 워크스페이스 `D:\InquiryFoundry`). 직전에 **하드 크래시** 1회 — §7.5.
다음 세션은 이 파일을 먼저 읽고, 기본 역할은 **OA**다. 벤더 LWAR을 OA가 띄우지 않는다.

호칭: 정욱님. 한국어 응답, 코드/경로/식별자는 English. 로컬 스킬만 (`.agents/skills`).

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
- `registry_version`: **33**
- 슬롯 **0개**. 2026-08-19에 로스터를 통째로 비웠다.

| 슬롯 | 처분 | 사유 |
|---|---|---|
| LWAR6 (xai) | `deregistered` — LWAR 주도 정규 은퇴 | Grok이 해지 요청. `on→draining→off→deregistered` 를 OA가 `reconcile` 로 단계 승인 |
| LWAR1 (alibaba) | `retire-stale` | 28시간 고아. IF 배제 대상이라 되살려도 못 쓴다 |
| LWAR5 (moonshot) | `retire-stale --abandoned-task-id` | 크레딧 소진 |
| LWAR4 (deepseek) | `retire-stale --abandoned-task-id` | 운영자가 세션 종료 |

  LWAR4·LWAR5 는 **claim을 쥔 채 죽어** heartbeat가 `running` 으로 얼어붙은 상태였다.
  일반 `--retire-stale` 은 `heartbeat_not_idle` 로 영구 거부한다 — §7.6 참조.

- **앞으로의 로스터: Codex / Antigravity / Grok.** 셋 다 `EXCLUDE_FAMILIES={alibaba}`,
  `EXCLUDE_ADAPTERS={qwen}` 에 걸리지 않고 `vendor_family` 도 3종이라 `normal` 모드의
  "2종 이상" 요건을 만족한다. `vendor_family`/`adapter_id` 는 스키마 enum이 아니라
  **LWAR이 등록 시 자기 신고**하는 자유 문자열이므로, 등록 후 `status` 로 실제 신고값을
  확인하고 배제 정책과 대조할 것.
- 슬롯 배정은 `lowest_available`. tombstone 의 `reusable_after` 가 지난 번호부터 재사용되므로
  새 런타임은 LWAR1 부터 순서대로 받는다.
- audit `healthy`, degraded/pending 0.

다음 OA: 새 `PAO_OA_ID` mint → `doctor --role oa` → `presence` → `reconcile` → `status`.
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

## 8. 다음 작업 (우선순위)

1. **새 로스터 등록 대기** — Codex / Antigravity / Grok. OA는 LWAR를 띄울 수 없다.
   등록되면 `reconcile` → `status` 로 신고된 `vendor_family`/`adapter_id` 를 배제 정책과 대조할 것.
2. **live5b(3회차 `scaling`)** — 브리프는 `_workspace/if-live5/brief-5b.yaml` 로 준비돼 있다.
   `avoid_patterns` 전량 배포(`61986b7`)가 재발을 막는지 확인한다. 교란 요인은 위 절 참조.
   런 중 감시는 `--busy-grace 960`.
3. live2 `review.yaml` 인간 adopt — 기계 금지.
4. 백로그: U11 D20 강제, U18 IfPhase2Roles — 아직 하지 않음.

OA `sanitize-idle`(work/·죽은 pid 청소)은 **미구현**. 전권 wipe 금지.

---

## 9. 하지 말 것

- `var/identities/` 스캔 후 남의 identity 채택 — **문서에 적힌 경로도 trusted handoff가 아니다**
- 유효 슬롯에서 재등록
- `.pao` / registry / lease / writer_lease 손편집
- OA가 벤더 CLI에 직접 지시 붙여넣기
- `lwar3_adp_loop.py` / `if_autorun.py`로 일반 PAO 태스크 처리
- live1 동결 해제, Qwen 재투입
- ADOPTED를 기계가 부여
- **살아있는 LWAR3를 정리 대상으로 착각** — 검증된 워커다

---

## 10. 다음 세션 부트스트랩

```text
1. HANDOFF.md + AGENTS.md + CLAUDE.md
2. 역할 OA → pao-oa SKILL.md
3. doctor --role oa → PAO_OA_ID mint → presence → reconcile → status
4. 스킬 작업이면 .pgf/DESIGN-PaoLwarV118.md 가 권위 (P1-P6 done)
5. IF 작업이면 .pgf/DESIGN-InquiryFoundry.md 가 권위
```
