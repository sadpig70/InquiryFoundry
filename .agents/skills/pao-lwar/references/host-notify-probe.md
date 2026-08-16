# First-session host notify probe

Run this **once per session**, after `doctor --role lwar` and **before**
the first `register` / `response` / `adp`. Do not skip it because
`adapter_id` looks familiar. Re-read only if this file or the runtime
version changes.

Two names:

| Name | Meaning |
|---|---|
| **live-notify** | This session receives watcher stdout **while the process is still running**. |
| **exit-notify** | This session receives watcher stdout **only after the process exits**. |

Codex is **exit-notify** plus a stricter delivery rule: a background
`TaskOutput` does **not** wake this session. Use a **blocking** tool so
the exited process's stdout is **this** call's result.

Do **not** sleep 50 minutes. Do **not** poll mailbox files.

## 1. Timeout option (`bg_timeout_50m`)

Question: when starting **background** Python, can this host's timeout
option be set to **50 minutes or more** (`>= 3000` seconds)?

The inspection is **complete** as soon as that question is answered.
Accepting the argument is enough. Do not wait for a process to actually
run 50 minutes.

| Result | When |
|---|---|
| `pass` | You can set the background-Python timeout to `>= 3000` s, or to an unlimited/zero value that means no cap. |
| `fail` | The host rejects `>= 3000` s, documents a max `< 3000` s, or has **no** timeout option you can set. |

How to decide, in order:

1. Read this host's tool/schema/docs for the background-command timeout
   parameter (name may be `timeout`, `timeout_ms`, `block_until_ms`, …).
2. If the documented maximum is `>= 3000` s, or unlimited/0, record `pass`.
3. If you are unsure, submit a **short** background Python call
   (`python -c "raise SystemExit(0)"`) **with timeout requested at
   `>= 3000` s**. If the host **accepts** the call (does not reject the
   timeout argument), record `pass`. If it rejects or clamps below
   3000 s, record `fail`.
4. Kill that short process if it is still running. Do not leave it up.

`fail` does **not** block LWAR. It only forbids a 50-minute **background**
slice. Official ADP is still the blocking `exit-notify` loop below.

## 2. Notify style (`notify_style`)

```bash
python -u "<PAO_SKILL>/scripts/host_notify_probe.py"
```

Start that as a **background** tool if this host has a background tool.
The script prints `PAO_LIVE`, sleeps 5 seconds, then prints `PAO_EXIT`.

| What this session sees | `notify_style` |
|---|---|
| `PAO_LIVE` **before** the process exits | `live-notify` |
| Both lines **only after** exit, in this session / this turn | `exit-notify` |
| Exit output does **not** appear as this session's tool result (only a later panel, or never) | `exit-notify` + `blocking_required=true` |

If the host has **no** background tool, skip the background launch.
Record `exit-notify` and `blocking_required=true`.

If the 5-second probe is inconclusive, record `exit-notify` and
`blocking_required=true` (safe default). Do not retry more than once.

## 3. Choose the watcher

After both results are recorded, enter §0.5 registration / ADP. Use
**exactly one** of the two bundled watchers. Do not write a third loop.

### exit-notify watcher

```bash
python -u "<PAO_SKILL>/scripts/adp_exit_notify.py" --identity-file IDENTITY
# same: lwar.py adp / adp-exit / adp-kimi --identity-file IDENTITY
```

Exits on the first task/control/fatal or after 50 idle minutes (`3000` s).
This session reads stdout, handles the event, then starts the **same**
script again. Fresh register still uses
`lwar.py response REQUEST_ID --resident --max-runtime-s 3000`.

### live-notify watcher

```bash
python -u "<PAO_SKILL>/scripts/adp_live_notify.py" --identity-file IDENTITY
# same: lwar.py adp-live --identity-file IDENTITY
```

Stays up. Each event is one stdout line **while the process is running**.
`begin` → work → `complete` without killing this process. Do not start a
second watcher. Fresh register uses
`lwar.py response REQUEST_ID --background`.

| `bg_timeout_50m` | `notify_style` | Watcher |
|---|---|---|
| any | `blocking_required=true` | **Blocking** `adp_exit_notify.py`. Do not background. Do not wait for a new turn. |
| `fail` | `exit-notify` | Same blocking `adp_exit_notify.py`. Do not start a 50-minute background slice. |
| `pass` | `exit-notify` | `adp_exit_notify.py`. Background start is allowed only if this session receives that child's stdout **on exit**. Prefer blocking. |
| `pass` | `live-notify` | `adp_live_notify.py` as a background tool with timeout >= 50 minutes (or unlimited). |

Never start `adp_live_notify.py` unless `notify_style=live-notify` **and**
`bg_timeout_50m=pass`. Never wrap either watcher in a custom loop that
captures stdout (`capture_output=True`) — that hides both styles from
this session.

Keep the two probe values in session memory. Do not write them into
mailbox paths, result `summary`/`evidence`, or artifact contents.
