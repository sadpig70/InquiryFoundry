# PaoServer Design @v:0.1.0

**Status** done (v0.1.0 구현·검증 완료 2026-08-25) · **Notation** PG v1.3 + PGF v2.5 · **Scale** Level 3 (16 nodes)
**Runtime** Rust 1.91 단일 바이너리 · MCP Streamable HTTP (127.0.0.1)
**승인된 결정** (2026-08-25 검토, 운영자 승인): 초인종 모델 · blocking tool long-poll · heartbeat 인수

이 문서가 pao-server 의 권위 설계다.

---

## Purpose

LWAR watcher 를 벤더별 상주 프로세스에서 **중앙 MCP 서버 하나**로 옮긴다.
파일 버스는 진실 원천으로 불변 — 서버는 **알림 계층**이다.

실측 근거(HANDOFF): watcher 소리 없는 사망(LWAR1 2h stale, ping 미수령) ·
바쁜 LWAR 이 stale 로 보임(exit-notify 가 heartbeat 를 쓰고 종료) ·
idle cap 재시작 누락. turn 소모는 **해결하지 않는다** — 가치는 신뢰성·관측성.

## Closed Decisions

| ID | Decision |
|---|---|
| S1 | **초인종, 집배원 아님.** 서버는 버스에서 파일을 옮기지도 지우지도 않는다. claim/lease/submit 은 기존 `lwar.py` 경로. 서버 사망 = 알림 유실뿐, claim 좌초 없음(§7.6 재발 방지) |
| S2 | **유일한 쓰기 2곳**: (a) 대기 중 LWAR 의 `heartbeat.json` — 기존 파일의 identity 필드를 보존하고 `last_seen`/`status` 만 갱신. 파일이 없으면 쓰지 않는다. (b) 서버 자신의 `\.pao/var/pao_server.json` |
| S3 | **blocking tool long-poll.** `watcher_wait(lwar_id, timeout_s)` — 서버측 상한 600s, 도착 즉시 반환. SSE push 안 씀(벤더 클라이언트 호환성) |
| S4 | **stateless MCP.** 세션 없음. POST 마다 JSON-RPC 1건, `application/json` 응답. GET /mcp = 405. Streamable HTTP 스펙이 허용하는 최소형 |
| S5 | **의존성 최소**: `serde` + `serde_json` 만. HTTP 는 std::net + thread-per-connection 수제(POST 2 종·GET 1 종만 필요). tokio/axum/rmcp 안 씀 — API 지식 리스크 제거, 오프라인 빌드 가능성 확보 |
| S6 | **5s 폴링, 파일 감시 안 씀.** `.pao-*.tmp` → rename 원자적 쓰기와 감시 API 의 상호작용 리스크 회피. 폴링 대상: registry `state ∈ {on, draining}` 슬롯의 `incoming/*.json` + `control/*.json` |
| S7 | **registry 파싱 fail-safe**: 파싱 실패 시 mailbox/ 하위 전 디렉터리 폴링으로 강등(경고 로그) |
| S8 | **127.0.0.1 바인딩 고정.** 인증 없음(로컬 전용 명시) |
| S9 | 서버는 `pao_runtime` 을 복사하지 않는다(PAO Invariant 8 존중). registry 는 `slots.*.state` 만 읽는다 — 스키마 드리프트에 관대 |

## Layout

```text
pao-server/
    Cargo.toml
    src/
        main.rs        # 인자 파싱, 스레드 기동
        bus.rs         # BusReader + HeartbeatWriter (파일 계약 전부 여기)
        poll.rs        # 5s Poller + WaiterHub (condvar)
        http.rs        # 수제 HTTP/1.1 (POST /mcp, GET /health)
        mcp.rs         # JSON-RPC dispatch (initialize, tools/list, tools/call)
        clock.rs       # UTC ISO8601(마이크로초+Z) — civil-from-days 수제
    tests/
        protocol.py    # 실제 HTTP 로 MCP 왕복 검증 (파이썬 클라이언트)
```

## Gantree

```
PaoServer // 중앙 watcher MCP 서버 (done) @v:0.1.0
    Scaffold // cargo init + 의존성 잠금 (done)
        # process: cargo new, serde/serde_json 추가, 빌드 확인
        # criteria: cargo build 성공
    Clock // UTC ISO8601 포맷 (done)
        # input: SystemTime
        # process: epoch → civil-from-days → "%Y-%m-%dT%H:%M:%S%.6fZ"
        # criteria: 파이썬 datetime 출력과 문자열 일치
    BusReader // 버스 읽기 전용 뷰 (done) @dep:Scaffold
        RegistryView // slots.*.state 만 파싱, fail-safe (done)
        MailboxScan // incoming/control *.json 개수 (done)
    HeartbeatWriter // S2 계약의 쓰기 2곳 (done) @dep:Clock,BusReader
    WaiterHub // lwar_id 별 대기자 + condvar 신호 (done) @dep:Scaffold
    Poller // 5s 루프 (done) @dep:BusReader,WaiterHub,HeartbeatWriter
    Http // 수제 HTTP/1.1 서버 (done) @dep:Scaffold
    Mcp // JSON-RPC 디스패치 (done) @dep:Http,WaiterHub
        WatcherWait // blocking tool (done)
        WatcherStatus // 상태 tool (done)
    UnitTests // clock·registry·mailbox 단위 테스트 (done) @dep:Mcp
    ProtocolTest // 파이썬 클라이언트 실왕복 (done) @dep:UnitTests
    Verify // 3관점 교차 검증 (done) @dep:ProtocolTest
    Docs // README + HANDOFF + CLAUDE.md 갱신 (done) @dep:Verify
```

## PPR

### Poller

```python
def poller_loop(bus: BusReader, hub: WaiterHub, hb: HeartbeatWriter):
    """5초마다 버스를 훑고 대기자를 깨운다."""
    while running:
        lwars = bus.watchable_lwars()          # S7: 실패 시 전 디렉터리
        for lid in lwars:
            n_task = bus.count(lid, "incoming")
            n_ctl  = bus.count(lid, "control")
            if n_task or n_ctl:
                hub.wake(lid, {"tasks": n_task, "controls": n_ctl})
            if hub.is_waiting(lid):
                hb.touch_lwar(lid, status="watching")   # S2(a)
        hb.touch_server(watching=hub.waiting_ids())     # S2(b)
        sleep(5)
    # acceptance_criteria:
    #   - 메시지 존재 시 다음 폴 안에(<=5s) 해당 대기자만 깨어난다
    #   - heartbeat.json 이 없는 LWAR 에는 어떤 파일도 생기지 않는다
    #   - identity 필드(instance_id, generation, lwar_id)가 보존된다
```

### WatcherWait (MCP tool)

```python
def watcher_wait(lwar_id: str, timeout_s: int = 240) -> dict:
    """도착 즉시 또는 timeout 에 반환. 파일은 건드리지 않는다(S1)."""
    timeout_s = min(max(timeout_s, 1), 600)
    hub.register(lwar_id)
    # 즉시 검사 1회 — 이미 와 있으면 폴링 5s 를 기다리지 않는다
    counts = bus.snapshot(lwar_id)
    if counts.any(): return arrived(counts)
    counts = hub.wait(lwar_id, timeout_s)      # condvar
    return arrived(counts) if counts else {"arrived": False}
    # acceptance_criteria:
    #   - 반환 스키마: {arrived, tasks, controls, lwar_id, waited_ms}
    #   - 이미 도착해 있던 메시지는 폴 주기와 무관하게 즉시 반환
    #   - 동일 lwar_id 중복 대기 허용(둘 다 깨어남)
```

### Mcp dispatch

```python
def handle(req: JsonRpc) -> JsonRpc:
    match req.method:
        case "initialize":       return init_result(protocolVersion=req.params.protocolVersion or "2025-03-26")
        case "notifications/initialized": return HTTP_202
        case "tools/list":       return [watcher_wait_schema, watcher_status_schema]
        case "tools/call":       return dispatch_tool(req.params)
        case "ping":             return {}
        case _:                  return error(-32601)
    # acceptance_criteria:
    #   - initialize → tools/list → tools/call 왕복이 파이썬 클라이언트로 검증됨
    #   - 알 수 없는 method 에 -32601, 깨진 JSON 에 -32700
```

## Invariants

1. 서버는 mailbox 의 어떤 파일도 이동·삭제·생성하지 않는다 (heartbeat.json 갱신만 예외)
2. heartbeat 는 **기존 파일이 있을 때만** 갱신 — identity 필드 보존, `last_seen`/`status` 만
3. 바인딩은 127.0.0.1 하드코딩 — 인자로도 바꿀 수 없다
4. registry 파싱 실패는 치명이 아니다 — 전 디렉터리 폴링으로 강등
5. 서버 사망이 claim 을 좌초시키지 않는다 (서버는 claim 을 모른다)

## Deterministic / AI boundary

전부 결정론 코드다. `AI_` 노드 없음 — 이 시스템의 AI 는 서버의 **클라이언트**(LWAR)다.
