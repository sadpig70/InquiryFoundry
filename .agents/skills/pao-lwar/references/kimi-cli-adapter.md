# Kimi / all-host official ADP (resident exit)

This path is now the official ADP for **every** host, not only Kimi.
Claude/Codex `--background` inject is optional and not required.

Kimi has **no live stdout inject**. A Python process that is still running
does not deliver mid-run stdout into a new agent turn. A **finished**
process delivers its stdout (completion notify or one `TaskOutput`).

Kimi can keep one Python tool blocked for about **1 hour**. Stay under that
with a 50-minute cap (`3000` seconds).

Do **not** poll mailbox files or event files in a tool loop. That burns the
per-turn call cap.

## Official path: exit, read stdout, handle, restart

After identity adoption:

```bash
python -u "<PAO_SKILL>/scripts/lwar.py" adp --identity-file IDENTITY
```

(`adp-kimi` is the same command.)

Equivalent explicit form:

```bash
python -u "<PAO_SKILL>/scripts/adp_watch.py" \
  --identity-file IDENTITY \
  --resident \
  --max-runtime-s 3000
```

Fresh register (no identity yet):

```bash
python -u "<PAO_SKILL>/scripts/lwar.py" response REQUEST_ID \
  --resident \
  --max-runtime-s 3000
```

`--resident` now waits in-process for OA approval (same as `--background`).
If 50 minutes pass with no approval, it prints `registration_pending`
(`reason=max_runtime`, exit 2). Restart the **same** `response` command.

Start the command as a **background** tool (`python -u`). Do not poll.
When the process **exits**, read stdout.

### One-time host check

Before the first live ADP, run [host-notify-probe.md](host-notify-probe.md).
Kimi is expected **exit-notify** (no live inject). `bg_timeout_50m` is
`pass` only if this host lets you **set** a background-Python timeout to
>= 50 minutes; do not sleep 50 minutes to prove it.

If `notify_style` is not exit-notify-with-this-turn delivery, run
`adp_exit_notify.py` (or `lwar.py adp`) as a **foreground** blocking
tool. Do not run `adp_live_notify.py` on Kimi.

## After stdout

Process **every** JSON line, last event wins for restart policy.

| stdout `event` | exit | Kimi |
|---|---:|---|
| `identity_adopted` | (then continues) | Remember `identity_file`. Do not treat this as the only reason to stop. |
| `task_received` | 0 | `begin` → work → `complete --result-file`. **Then** restart watcher. |
| `control` (`drain` / `cancel` / `ping`) | 20 | Handle the control. Then restart watcher. |
| `control` (`shutdown`) | 20 | Submit any held claim. **Do not restart.** |
| `control` (`retire`) | 20 | `lwar.py retire` until `lwar_retired`. **Do not restart.** |
| `idle_timeout` (`reason=max_runtime`) | 10 | No work. Restart the **same** watcher command. |
| `registration_pending` (`reason=max_runtime`) | 2 | Still waiting for OA. Restart the same `response` command. |
| `adp_error` | 30 | Stop. Do not auto-restart. Report. |
| `invocation_superseded` | 40 | This invocation lost. Do not execute. Restart only if you still own the identity. |

### Restart rules

1. Restart **only after** `complete` for the current claim. Starting a new
   watcher first re-emits `recovered_claim` and races `begin`.
2. "비우기" = `begin` + `complete`. Do **not** delete mailbox JSON, `claimed/`,
   or `incoming/` by hand.
3. `idle_timeout` / `registration_pending` → same command, immediately.
4. `shutdown` / successful `retire` → **never** restart.
5. Do not start a second watcher while the first process is still alive.

Shortcut after the first `identity_file` is known:

```bash
python -u "<PAO_SKILL>/scripts/lwar.py" adp-kimi --identity-file IDENTITY
```

`adp-kimi` forces `--resident` and defaults `--max-runtime-s` to `3000`.
Identity may also come from `PAO_LWAR_IDENTITY`.

## Not the Kimi primary path

| Mechanism | Use |
|---|---|
| `--background` (infinite daemon) | Claude / Codex stdout-notify hosts only |
| `--detach` + event file | Only if you cannot take stdout on process exit |
| `lwar.py adp-wait` | Only with `--detach` (file wait). Do not poll it in a loop |
| `kimi_adp_recycle.py` | Secondary: only if a **detached** child is still reaped by the 1h job |

`--detach` plus agent-side file polling is forbidden. If detach is required,
block once with `adp-wait --timeout 3300`, handle one line, then `adp-wait`
again — do not restart `adp_watch`.

## What this does **not** change

- `begin` / `complete --result-file` / fence tokens
- `if_lwar.py` import: sibling `.agents/skills/if-core` only. Run
  `python .agents/skills/if-lwar/scripts/if_lwar.py --self-test` (expect `ok`)
- Visibility jail, no `question_id` mint
- Do not use `--background` and `--resident` together
