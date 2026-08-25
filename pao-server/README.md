# pao-server

PAO LWAR watcher 를 벤더별 상주 프로세스에서 **중앙 MCP 서버 하나**로 옮긴다.
파일 버스는 진실 원천으로 불변 — 이 서버는 **알림 계층(초인종)** 이다.

- MCP Streamable HTTP, stateless, **127.0.0.1 고정** (하드코딩, 인자로도 못 바꿈)
- 5초마다 registry 의 `on`/`draining` 슬롯의 `incoming/`·`control/` 을 훑는다
- 버스의 파일을 **옮기지도 지우지도 만들지도 않는다** — claim/lease/submit 은 기존 `lwar.py` 경로 그대로
- 쓰기는 정확히 2곳: 대기 중 LWAR 의 `heartbeat.json`(identity 보존, `last_seen`/`status` 만) · 서버 자신의 `.pao/var/pao_server.json`

권위 설계: [`../.pgf/DESIGN-PaoServer.md`](../.pgf/DESIGN-PaoServer.md) (결정 S1–S9, Invariants)

## 빌드·실행

```bash
cargo build --release          # 의존성: serde, serde_json 뿐
./target/release/pao-server.exe --root D:/InquiryFoundry/.pao --port 8811
# --poll-secs 5 (기본)
```

기동 확인: `curl http://127.0.0.1:8811/health`

## LWAR 런타임에 등록

각 벤더 런타임의 MCP 설정에 Streamable HTTP 서버로 추가한다:

```
URL: http://127.0.0.1:8811/mcp
```

(Claude Code 예: `claude mcp add --transport http pao-watcher http://127.0.0.1:8811/mcp`)

## LWAR 의 사용 계약

```
1. watcher_wait(lwar_id="LWAR1", timeout_s=240) 호출 → 블로킹
2. {arrived: true, tasks: N, controls: M} 반환 → 기존 lwar.py 로 claim·처리·submit
   {arrived: false} 반환 → 다시 watcher_wait 호출
3. 반복
```

서버는 도착 **개수만** 알려준다. 메시지 본문은 버스에 그대로 있다.

## Tools

| tool | 동작 |
|---|---|
| `watcher_wait(lwar_id, timeout_s?)` | 도착 즉시 또는 timeout(상한 600s, 기본 240s)에 반환 |
| `watcher_status()` | 서버 생사·대기 중 목록·감시 대상 목록 |

## 테스트

```bash
cargo test                     # 단위 14건 (clock/bus/poll/mcp)
python tests/protocol.py       # 실 HTTP 왕복 26건 — 스크래치 버스에 실바이너리
```

## 운영 메모

- 서버가 죽으면 **알림만 멎는다.** claim 좌초 없음 — 서버는 claim 을 모른다
- 서버 생사는 `.pao/var/pao_server.json` 의 `last_seen` 으로 판정 (5초마다 갱신)
- registry 파싱 실패 시 mailbox 전 디렉터리 폴링으로 강등 (경고만, 침묵하지 않음)
- turn 소모는 이 서버가 해결하지 않는다 — LWAR 은 깨어날 때마다 여전히 turn 을 쓴다.
  가치는 **watcher 사망·stale 오판·재시작 누락의 제거**다
