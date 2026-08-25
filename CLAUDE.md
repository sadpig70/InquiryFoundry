# CLAUDE

→ Read [`AGENTS.md`](AGENTS.md)

## PAO role routing

- Default role is `OA`; load `.agents/skills/pao-oa/SKILL.md`.
- `OA` never launches a vendor LWAR. It communicates through `python .agents/skills/pao-oa/scripts/oa.py` and the file bus.
- A runtime receiving `/lwar-register [number]` becomes an `LWAR`; load `.agents/skills/pao-lwar/SKILL.md`.
- An `LWAR` with the `pao-watcher` MCP tools (pao-server, `http://127.0.0.1:8811/mcp`) skips the host probe: loop `watcher_wait(lwar_id)` → on arrival run `adp_exit_notify.py` once to claim and handle → wait again. Without the MCP tools it runs the once-per-session host-notify probe and starts **one** bundled watcher matching the probe result (default exit-notify: blocking `scripts/adp_exit_notify.py`, restart after each event; `adp_live_notify.py` is the live-notify-only path). The server is start-by-operator/OA: `pao-server/target/release/pao-server.exe --root .pao --port 8811`.
