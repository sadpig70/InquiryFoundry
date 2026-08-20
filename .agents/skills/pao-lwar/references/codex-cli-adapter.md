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
python -u "<PAO_SKILL>/scripts/lwar.py" adp --identity-file IDENTITY --max-runtime-s 3000
```

Run that as a **foreground / blocking** tool (`python -u`). One call sleeps
until the first task/control or 50 minutes.

### Preferred no-cell blocking envelope

On a Codex code-mode host that exposes `functions.exec` and a nested shell
tool, keep the original tool call pending longer than the watcher and keep the
shell timeout longer than both. Use this ordering:

```text
watcher max runtime:          3000 s
functions.exec yield_time_ms: 3120000 ms (3120 s)
shell timeout_ms:             3180000 ms (3180 s)
```

The required invariant is `watcher runtime < exec yield window < shell
timeout`. Invoke the shell tool once inside `functions.exec`, await it, and
return its final result. Do not call `yield_control`, do not request a
background launch, and do not call `wait` while the original call remains
pending. When the watcher exits, the original `functions.exec` call returns its
stdout and exit code directly in this turn, with no cell ID.

Host progress notices are optional. If the host requires them, emit only
out-of-band status notices that do not yield the tool call, inspect the mailbox,
poll the process, or capture watcher stdout.

This exact timeout envelope completed a live 3060-second foreground Python
probe on the current Codex host with one PID, exit 0, no cell ID, and no `wait`
call. That probe establishes host blocking capacity only; it did not execute an
ADP task or validate task handling.

### Unexpected host-managed cell yield (fallback)

Some Codex hosts may return `Script running with cell ID ...` before the
foreground watcher exits. This is a host-managed yield of the blocking tool,
not watcher completion, a timeout, `--background`, or a detached process. The
shell and watcher remain alive under that exact cell.

When this happens, stay in the same turn and invoke the host's `wait` operation
on the exact returned cell ID. If the wait window expires and returns the same
live cell ID, wait on that cell again. Do not end the turn, start another
watcher, re-register, or infer failure from the yield. Only handle watcher
stdout after the retained cell reports output/completion according to the
host's wait contract. A wait on the execution cell is the blocking continuation
of the original tool call; it is not mailbox or event-file polling.

If the cell disappears or cannot be waited without returning the watcher's
terminal output, fail closed and report a host-delivery error. Do not recover by
starting a second watcher or registering a new identity.

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
