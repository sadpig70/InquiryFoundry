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

## Residual / deferred (v0.3)

- TaskJail per-task + host capability (Codex C1)
- MineMin OA-side U-id (Codex C5)
- RunJournal / InvariantLedger / ClaimRegistry
- 인간 게이트 4종을 pass\|fail\|waived로 집행
- OS 샌드박스

## Next

`/PGF plan InquiryFoundry` → `.pgf/WORKPLAN-InquiryFoundry.md`
