# CLAUDE

→ Read [`AGENTS.md`](AGENTS.md)

## PAO role routing

- Default role is `OA`; load `.agents/skills/pao-oa/SKILL.md`.
- `OA` never launches a vendor LWAR. It communicates through `python .agents/skills/pao-oa/scripts/oa.py` and the file bus.
- A runtime receiving `/lwar-register [number]` becomes an `LWAR`; load `.agents/skills/pao-lwar/SKILL.md`.
- An `LWAR` adopts its identity, then starts **one** background `adp_watch.py --background --report-every 86400` (or `lwar.py response REQUEST_ID --background`) and ends the turn. It does not loop watcher slices in one turn.
