# Codex CLI adapter (mandatory if adapter_id is `codex`)

Codex does **not** start a new agent turn when a background Python process
prints JSON or even when it exits. `TaskOutput` sitting in the host does
not wake this session. `Start-Process` / detached / orphan watchers print
into nowhere.

Therefore Codex MUST treat ADP as a **blocking tool in this same turn**.
The watcher exits; this turn receives stdout; this turn handles it; this
turn starts `adp` again. Do not wait for the operator.

## Forbidden on Codex

- `Start-Process`, `Start-Process -PassThru`, `nohup`, `DETACHED_PROCESS`
- `lwar.py response … --background` and `adp_watch.py --background`
- `--detach`, `adp-wait`, `kimi_adp_recycle.py`
- Ending the turn after starting a watcher
- Polling mailbox / event files in a tool loop
- Re-registering because a tool timed out
- Waiting for a "new Codex turn" after watcher stdout

## Official loop

Identity — use only a path this session was handed directly by the operator or
emitted by its own earlier watcher event:

```text
<BUS_ROOT>\var\identities\<instance_id>.json
```

If that file still matches `lwar.py status` exit 0, do **not** register. Never
adopt a path found by scanning `var/identities/` or copied out of a document:
a documented path is not a trusted handoff, and adopting it steals another
session's slot.

```bash
python -u "<PAO_SKILL>/scripts/lwar.py" adp --identity-file IDENTITY
```

Run that as a **foreground / blocking** tool (`python -u`). One call sleeps
until the first task/control or 50 minutes.

| stdout `event` | this turn |
|---|---|
| `task_received` | `begin` → work → `complete --result-file` → **same** `adp` again |
| `control` drain/cancel/ping | handle → `adp` again |
| `control` shutdown / successful retire | stop. do not restart |
| `idle_timeout` (exit 10) | **same `adp` immediately**. this is not a stop |
| `adp_error` | stop and report |

`idle_timeout` is a normal cap. Not restarting it is a skill violation.

Fresh register only if status exit 3/4:

```bash
python -u "<PAO_SKILL>/scripts/lwar.py" response REQUEST_ID --resident --max-runtime-s 3000
```

Same blocking rule.

## One-time host check

Before the first `adp`, run [host-notify-probe.md](host-notify-probe.md).
Codex is **exit-notify** with `blocking_required=true`: stdout must be
**this** tool call's result, not a later turn or a background Task panel.
`bg_timeout_50m=pass` only means the timeout **option** can be set to
>= 50 minutes — it does **not** authorize `adp_live_notify.py` or
`--background` on Codex. Always `adp_exit_notify.py` as a blocking tool.
