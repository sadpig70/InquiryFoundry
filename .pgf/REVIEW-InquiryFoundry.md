# REVIEW-InquiryFoundry

## Scope
- Target: `.pgf/DESIGN-InquiryFoundry.md`
- Versions: v0.2.2 → **v0.2.3**
- Date: 2026-08-14
- Mode: design-review cycle 3 (apply `_workspace/IF_upgrade_plan.md`)
- Input reviews: claude / codex / kimi / qwen `*_IFv0.2.2_review.md`
- Decisions accepted: **D19, D20, D21**

## Summary

4 LWAR 후보 리뷰를 교차한 뒤 Wave0 3건을 기본값으로 확정하고 Wave1 fail-closed를 DESIGN에 패치했다. cycle 2 APPROVED는 철회되었고, v0.2.3이 그 구멍을 닫는다.

## Verdict

| Item | Result |
|---|---|
| D19 kill threshold | `kills >= 1` |
| D20 diversity | pair = 런 내부만; prior = domain+최근 50, mean only; `th_mean=0.40 < th_pair=0.55` |
| D21 REJECTED cards | informational, adopt 금지, `record_decision`만 |
| Wave1 fail-closed | patched into v0.2.3 |
| Residual High | 1건 — jail은 PAO permissions 근사 (OS 샌드박스는 v0.3 TaskJail) |
| **Aggregate** | **APPROVED for plan** (Critical=0, High=1) |

## Applied (v0.2.3)

- close: `preflight_close` → mutation. REVIEWED 재적용. V11/V15
- DORMANT wound ∈ dissent_portfolio. V13
- `inject_divergence(alloc, brief)` + `hint_strings` 갱신 + `materialize_hints` 재호출. deepcopy. V17
- `materialize_qo` 필수 필드. `reuse_or_mint` 멱등
- `dissent_report_outbox` 분리. V16
- `mint_anon` = HMAC(run_nonce). V18
- `stamp_lineage` OA 덮어쓰기. V12
- `protocol_valid` 관측 공식. `vis_ok` 상수 삭제
- 빈 시드 ≠ `diversity_failed`. V14
- IfOa에서 `doctor` 삭제. `send --lwar-id`. 터미널 어휘 정합
- `network=False`. `ensure_jail`. 결정론 `task_id`
- Pareto 축에서 `impact` 제거. `all_scored` 병기
- normal: dissent 누락 → `Blocked(protocol_incomplete)`
- `source_in_hints` 최소 길이 6
- prior cap domain+50
- phase2 actor 예약
- edges `(src,rel,dst)` 멱등. version++
- helpers: `phase_of`, `path_allowed`, `template_restyle`, `make_generate_inbox`, `flatten_seeds`

## Applied (v0.2.4) — 운영 실측이 설계를 뒤집은 건

design-review 가 아니라 **라이브 런 13회의 실측**이 근거다. v0.2.3 이 규정한 것 중
하나는 해롭다고 판명돼 뒤집혔고, 나머지는 그 뒤 코드에만 있던 것을 설계로 올린 것이다.

- **뒤집힘 — `avoid_all[i::len(lwars)]` 슬라이싱.** v0.2.3 Allocate 노드가 회피 정보를
  슬롯별로 쪼개도록 규정했고 수용 기준이 "전 LWAR 동일 배열 금지" 였다. live4b 에서
  패턴을 받은 LWAR 은 전부 그 함정을 피했고 받지 못한 LWAR 이 둘 다 재현했다.
  전원 동일 배급으로 바꿨다. D22, Invariant 9.
- 회피는 두 블록 — 지속(`avoid_registry`, 코드) + 축어 창(`avoid_patterns`). D23
- 택소노미 통제는 `brief.withhold_avoid_codes`. `ratified` 강하로 대체 불가. D24
- `brief.constraints` 를 생성기·리뷰어에 실제로 전달. 예산 조항 금지. D25
- 파생 뷰 비권위. `store.avoid_registry(domain)` 로 질의. D26
- `run_operator_offset` — 슬롯 고정 연산자가 결정론 생성기에게 바이트 동일 입력을 줬다
- Feedback contract 절 신설 — 필드가 누구에게 가고 어느 것이 루프를 먹이는지
- Invariants 9–12 (전원 배급 / 기계 종결 불가 / append-only 판정 / 파생 비권위)

사고 기록은 `HANDOFF.md` §7.7–§7.26 이다. 이 문서는 무엇이 바뀌었는지만 남긴다.

## Residual / deferred (v0.3)

- TaskJail per-task + host capability (Codex C1)
- MineMin OA-side U-id (Codex C5)
- RunJournal / InvariantLedger / ClaimRegistry
- 인간 게이트 4종을 pass\|fail\|waived로 집행
- OS 샌드박스

## Next

`/PGF plan InquiryFoundry` → `.pgf/WORKPLAN-InquiryFoundry.md`
