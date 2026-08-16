# CLAUDE

→ Read [`AGENTS.md`](AGENTS.md)

## PAO role routing

- Default role is `OA`; load `.agents/skills/pao-oa/SKILL.md`.
- `OA` never launches a vendor LWAR. It communicates through `python .agents/skills/pao-oa/scripts/oa.py` and the file bus.
- A runtime receiving `/lwar-register [number]` becomes an `LWAR`; load `.agents/skills/pao-lwar/SKILL.md`.
- An `LWAR` runs the once-per-session host-notify probe, then starts **one** watcher matching the probe result. Default is exit-notify: blocking `scripts/adp_exit_notify.py` (`lwar.py adp`), which exits on the first event or after the idle cap — this session reads that stdout, handles the event, and restarts the same script. `--background` / `adp_live_notify.py` is the live-notify-only path.
