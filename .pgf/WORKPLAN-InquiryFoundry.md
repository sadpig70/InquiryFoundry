# InquiryFoundry Work Plan

**Status** done (IfPhase2Roles blocked) · **Source** `.pgf/DESIGN-InquiryFoundry.md` @v:0.2.3
**PPR authority** DESIGN (이 문서는 PPR을 복제하지 않는다)
**Review** `.pgf/REVIEW-InquiryFoundry-Workplan.md`

---

## POLICY

```python
POLICY = {
    "_version":            "2.6",
    "max_retry":           3,
    "on_blocked":          "halt",
    "design_modify_scope": ["impl", "internal_interface"],
    "completion":          "all_done_or_blocked",
    "max_iterations":      50,
    "design":              ".pgf/DESIGN-InquiryFoundry.md",
    "build_gate":          "qo_count == seed_count and seed_count > 0",
    "slo_not_gate":        "scored_count >= 8",
    "v_tests":             "V1-V18",
}
```

`halt`: fail-closed 계약(D19–D21, Independent First)을 skip으로 우회하지 않는다.
`IfPhase2Roles`는 DESIGN과 같이 `(blocked)`로 남긴다. 그룹 노드 `done` = 자식이 모두 terminal (`blocked` 포함).
실행기는 **노드 자신의 `@dep:`** 와 **조상 그룹이 막히지 않음**을 함께 본다. `IfCycle` 자식은 `IfCycle`의 `@dep:`가 충족되기 전에 시작하지 않는다.

---

## Execution Tree

```
InquiryFoundry // IF MVP 구현 (done) @v:0.2.3
    IfCore // 규약 + 결정론 I/O (done)
        [parallel]
        SchemaPack // schemas + validate.py (done)
            # Task: if-core/schemas 작성 (brief, seed_outbox, qo, dissent_report_outbox,
            #       dissent_report, score_card_outbox, review, report, decision_rec, edges)
            # Target: .agents/skills/if-core/schemas/
            # Output: validate.py (pass/fail CLI)
            # criteria: 샘플 3건 pass/fail 정확. V4, V10, V16 fixture
        OperatorPack // operators/registry.yaml (done)
            # Task: 12 operator id/template + propose_operator 거절 규칙
            # Target: .agents/skills/if-core/operators/registry.yaml
            # criteria: OPERATORS 12종, id 충돌 0
        GatePack // gates + mechanical_gates (done)
            # Task: hard_gates.yaml + source_in_hints(len>=6) + MECH/HUMAN 분리
            # Target: .agents/skills/if-core/gates/
            # criteria: G-FALSIFY 이름 없음. HUMAN을 mechanical fail로 강제하지 않음
        StatePack // LEGAL + assert_transition (done)
            # Task: 상태 전이표, ADOPTED human-only, phase2→QUARANTINE only
            # Target: .agents/skills/if-core/gates/state.yaml 또는 store.py
            # criteria: 불법 전이 거절 fixture. REVIEWED 재적용 허용
        [/parallel]
        StoreIo // id lock, QO I/O, local_id_map (done) @dep:SchemaPack,StatePack
            # Task: store.py — alloc_question_id, reuse_or_mint, write_question,
            #       append_edges 멱등, query_avoid_patterns
            # Target: .agents/skills/if-core/scripts/store.py
            # criteria: first write=DRAFT. 워커 alloc 호출 거절(V9). 재실행 mint 0
        BusContract // PAO envelope, jail, publish_collect (done) @dep:SchemaPack
            # Task: bus.py — phase_of, path_allowed, ensure_jail, make_pao_task,
            #       publish_collect(--lwar-id, poll, succeeded만 수용)
            # Target: .agents/skills/if-core/scripts/bus.py
            # criteria: doctor 없음. network=False. task_id=task-if-...
    IfRuntime // PAO 오버레이 (done) @dep:IfCore
        # Task: if-oa / if-lwar 폴더 골격. 런타임 포크 금지
        [parallel]
        IfOa // send/collect/recover/status/presence/audit-health (done) @dep:BusContract
            # Task: if_oa.py 래퍼. pao_runtime 복사 금지
            # Target: .agents/skills/if-oa/
            # criteria: if-oa/ 에 pao_runtime 0. 그래프 파일 쓰기 0
        IfLwar // begin → dispatch → complete --result-file (done) @dep:BusContract
            # Task: if_lwar.py + SKILL.md. jail 가시성, judge inbox 필드 금지
            # Target: .agents/skills/if-lwar/
            # criteria: --artifacts 플래그 없음. V1, V2, V9
        [/parallel]
    IfRoles // 인지 역할 스킬 (done) @dep:IfCore
        # Task: 역할 SKILL.md 3종. Phase2 착수 금지
        [parallel]
        IfGenerate // mine_min 2종, local_id only (done) @dep:OperatorPack,SchemaPack
            # Task: if-generate SKILL + mine_min/fill_seed. question_id 채우기 금지
            # Target: .agents/skills/if-generate/
            # criteria: evidence 없으면 drop. D18. unknown_ref 필수
        IfContrarian // 6유형, kills>=1 (done) @dep:SchemaPack
            # Task: if-contrarian SKILL. dissent_report_outbox. AI kill 금지
            # Target: .agents/skills/if-contrarian/
            # criteria: D19. question_id 필드 0 (V16)
        IfJudge // 블라인드, novelty 키 금지 (done) @dep:GatePack,SchemaPack
            # Task: if-judge SKILL + template_restyle. score_card_outbox
            # Target: .agents/skills/if-judge/
            # criteria: V2, V4, V10. scores 키 ⊆ testability,grounding,actionability[,impact]
        [/parallel]
        IfPhase2Roles // unknown-miner/novelty/action/safety (blocked) @dep:HumanClose
            # blocker: HumanClose 가 awaiting_human 까지 도달하지 않음
    IfCycle // if_cycle.py run|close (done) @dep:IfRuntime,IfGenerate,IfContrarian,IfJudge
        # Task: if-core/scripts/if_cycle.py run|close. PAO_OA_ID = 사이클 프로세스
        # criteria: protocol_valid 상수 금지. build_gate. V5
        Allocate // 배분표 결정론 로테이션 (done) @dep:OperatorPack,StoreIo,IfRuntime
            # Task: vendor_family 정규화, leftover_ops, avoid 분할
            # criteria: 동일 family+(ops,ev) 0. vendor_family 미기재 Blocked
        ExploreLoop // generate + Jaccard + divergence (done) @dep:Allocate,IfGenerate
            # Task: explore_loop, D20, inject_divergence+materialize_hints
            # criteria: 빈 시드 ≠ diversity_failed (V14). hints 3자 일치 (V17)
        ExploitLoop // contrarian → judge (done) @dep:ExploreLoop,IfContrarian,IfJudge
            # Task: stamp_lineage, mint_anon HMAC, rekey, normal dissent 필수
            # criteria: V12, V18. normal 누락 dissent → protocol_incomplete
        Compose // materialize_qo + 그래프 기록 (done) @dep:ExploitLoop,StoreIo
            # Task: compose(), local_id_map, dissent_log
            # criteria: validate(q) 첫 write 통과. ADOPTED 0. qo_count==seed_count
        HumanClose // preflight_close + REVIEWED 재개 (done) @dep:Compose
            # Task: open_review/close_review. Pareto 결정론 축. D21 informational
            # criteria: V7, V11, V13, V15. review.yaml 에 scores/generated_by 0
```

---

## Wave order (derived)

실행기는 `@dep:`만 따른다. 아래는 가독용 위상 정렬이다.

| Wave | Nodes | 대응 DESIGN |
|---|---|---|
| W0 | SchemaPack, OperatorPack, GatePack, StatePack | M1 |
| W1 | StoreIo, BusContract | M2 + M3 계약 |
| W2 | IfOa, IfLwar | M3 overlay |
| W3 | IfGenerate, IfContrarian, IfJudge | M4 |
| W4 | Allocate → ExploreLoop → ExploitLoop → Compose → HumanClose | M5 |
| — | IfPhase2Roles | M6 blocked |

루트 `InquiryFoundry`는 W4+HumanClose가 `done`이고 `IfPhase2Roles`가 `blocked`일 때 종료한다.

---

## Fixture contract

```text
tests/if/fixtures/
    valid_qo.yaml / invalid_qo.yaml / judge_outbox_with_qid.yaml
    v11_reviewed_resume/  v12_forged_lineage/  v13_dormant_wound/
    v14_empty_unknowns/   v15_ablation_adopt/  v16_contrarian_qid/
```

M1에서 스키마 fixture, M5에서 사이클 fixture. 라이브 LWAR≥3은 M5의 **별도** 수락 항목이며 CI 게이트가 아니다.
