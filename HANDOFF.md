# HANDOFF — InquiryFoundry

세션 종료 시점: 2026-08-16 (OA = Claude Opus 5, 워크스페이스 `D:\InquiryFoundry`).
다음 세션은 이 파일을 먼저 읽고, 기본 역할은 **OA**다. 벤더 LWAR을 OA가 띄우지 않는다.

호칭: 정욱님. 한국어 응답, 코드/경로/식별자는 English. 로컬 스킬만 (`.agents/skills`).

---

## 1. Git

- Remote: https://github.com/sadpig70/InquiryFoundry (public)
- Branch: `main` tracking `origin/main`. **HEAD = `2cad9a9`, push 완료** (워킹 트리 clean)
  - `90720c6` pao-lwar: unify the official ADP path on exit-notify (v1.17 doc debt)
  - `722b480` pao: add fenced recovery for slots OA could not reclaim
  - `062fae4` pgf: add the v1.18 design driving the pao-lwar changes
  - `2cad9a9` handoff: record the v1.18 session state
- 작업 브랜치 `pao-lwar-v1.18`은 fast-forward merge 후 삭제됨. 되돌릴 단위는 위 4개 커밋.

올리지 말 것: `.pao/`, `.if/`, `_workspace/`, `.env`, identity, mailbox. (`.gitignore`가 이미 처리)

**주의**: 통합 리뷰 원본 `_workspace/lwar-skill-review/*.md`는 **gitignore되어 리포에 없다**. 로컬에만 존재하며 설계 문서의 유일한 근거 자료다.

---

## 2. 역할 / 스킬

| 역할 | 스킬 | 비고 |
|---|---|---|
| OA (기본) | `.agents/skills/pao-oa/SKILL.md` v1.37 | `python .agents/skills/pao-oa/scripts/oa.py` + `.pao`만 |
| LWAR | `.agents/skills/pao-lwar/SKILL.md` (헤더는 아직 **v1.17**, 내용은 v1.18 진행분 반영) | 벤더 세션에서 `/pao-lwar` |
| IF overlay | `if-oa`, `if-lwar`, `if-core`, `if-generate`, `if-contrarian`, `if-judge` | |

권위 설계: IF는 `.pgf/DESIGN-InquiryFoundry.md` v0.2.3. **스킬 개선은 `.pgf/DESIGN-PaoLwarV118.md`.**

Python: PATH의 `python`. Shell: Git Bash 또는 PS7 (`D:\Tools\PS7\7.6.4\pwsh.exe`). PS 5.1 금지.

---

## 3. 버스 / 등록 (지금)

- Bus: `D:\InquiryFoundry\.pao`
- `registry_version`: **16**
- 슬롯: **LWAR3 only**, generation **2**, `on`, `runtime_status=active` (watcher 정상 동작 중)
  - `instance_id`: `lwar-instance-dbaa67bc3bbe44c8a0a852188c4e8d8b`
  - profile: Grok Build TUI / `adapter_id=grok_build` / `vendor_family=xai`
  - **실제 태스크를 완수하고 accepted 받은 검증된 LWAR다** (§5). 함부로 은퇴시키지 말 것.
- 이번 세션에서 회수한 슬롯 (tombstone에 generation 보존):
  - **LWAR1** — Grok 스모크 슬롯. 미수령 `shutdown` control 만료 후 `retire-stale`. mode `stale_idle_reap`
  - **LWAR2** — DeepSeek 리뷰 세션이 남긴 미채택 등록. `reclaim-unadopted`. mode `unadopted_reap`
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

검증되지 **않은** 것: 이종 벤더 동시 3-LWAR, 50분 슬라이스 경계, cancel/drain 경로, 축소 `slice_s` 실동작.

---

## 6. 새 OA 명령 (protocol 1.4.2 유지)

`references/recover-maintain.md` 참조. 둘 다 기존 경로와 같은 펜스 강도이며 **살아있는 LWAR에 fail-closed**임을 라이브 버스에서 확인했다.

```bash
oa.py recover --reclaim-unadopted --lwar-id LWARn --instance-id … --generation N --unadopted-after 3600 --reason "…"
oa.py recover --expire-controls    --lwar-id LWARn --instance-id … --generation N --control-older-than 600 --reason "…"
```

- `--reclaim-unadopted` — 승인됐으나 **identity 미채택** 슬롯. 해당 identity의 하트비트가 있으면 `identity_already_adopted`로 거부. 재실행 `already_reclaimed`
- `--expire-controls` — 죽은 watcher 앞 미수령 control. 원본 바이트 보존(`archive/control/` + `.expired.json` 사이드카). `retire-stale`이 `active_work: {"control": N}`로 막힐 때 **먼저** 실행

**런타임 사본 주의**: `pao_runtime/`은 두 스킬에 중복 배치돼 있다. `registry.py`/`oa_cli.py`는 byte-identical로 유지해야 한다. 단 `lwar_cli.py`/`adp_watch.py`/`pao_cli.py`는 **초기 커밋부터 이미 역할별로 상이**하며 통일 대상이 아니다. `runtime_version`을 한쪽만 올리면 모든 신규 등록이 `runtime_version_mismatch`로 거부된다.

---

## 7. 라이브 IF 런 (변화 없음)

| Run | 상태 |
|---|---|
| `RUN-20260814-live1` | **동결**. judge 연결 금지. dead-letter 1건(`…contrarian-LWAR3-r0`)은 requeue 금지 |
| `RUN-20260815-live2` | generate/contrarian/judge 3/3, compose 완료. `protocol_valid=true`, SCORED 8, REJECTED 1. human=`awaiting_human`. **ADOPTED는 인간만** |

데이터: `.if/runs/…` (git 제외). Qwen/`vendor_family=alibaba` 제외.
기계 게이트: G-GROUND, G-CLEAR, G-PATH, G-TESTSHAPE. D18–D21 유효.

---

## 8. 다음 작업 (우선순위)

1. **P5/P6** (`.pgf/DESIGN-PaoLwarV118.md`) — 결과·오류 계약(`complete` 멱등성, exit code 사전, 권한 게이트 `blocked`) + 위생 묶음. 전부 문서.
2. **`ProbeScriptUpgrade`** — P2의 유일한 미완 노드(`host_notify_probe.py` 타임스탬프 출력). `designing` 유지 중.
3. **SKILL.md 버전 헤더** — 아직 `v1.17`인데 내용은 v1.18 진행분. P5/P6 완료 시 `v1.18`로 올릴지 판단.
4. **벤더 다중 LWAR** — 현재 1대(LWAR3). 확장하려면 각 벤더 세션에서 정욱님이 `/pao-lwar` 실행 필요. OA는 못 함. 등록 후 OA가 `reconcile` → ack probe로 검증.
5. live2 `review.yaml` 인간 adopt — 기계 금지.
6. 백로그: U11 D20 강제, U18 IfPhase2Roles — 아직 하지 않음.

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
4. 스킬 작업이면 .pgf/DESIGN-PaoLwarV118.md 가 권위 (P5/P6 남음)
5. IF 작업이면 .pgf/DESIGN-InquiryFoundry.md 가 권위
```
