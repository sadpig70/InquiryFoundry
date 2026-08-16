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

## 1. Timeout capability

Record **three** values, not one. A single "can you set a 50-minute timeout?"
question cannot classify real hosts: several runtimes present the same
"no timeout option, but unbounded background" shape, and answering that one
question yields `pass`, `fail`, and "undecidable" for the same host.

Do **not** prove any of these by sleeping. Read the schema, or submit one short
call.

### 1a. Option acceptance (`bg_timeout_50m`)

Question: when starting **background** Python, can this host's timeout
option be set to **50 minutes or more** (`>= 3000` seconds)?

| Result | When |
|---|---|
| `pass` | You can set the background-Python timeout to `>= 3000` s, or to an unlimited/zero value that means no cap. |
| `pass` | The host has **no** timeout option at all, **and** background processes run unbounded, **and** their stdout reaches this session on exit. |
| `fail` | The host rejects `>= 3000` s, or documents a maximum `< 3000` s. |
| `fail` | The host has no timeout option and you cannot establish unbounded background execution with stdout delivery on exit. |

Precedence when two rows seem to apply: a **documented cap below 3000 s is
`fail`**, whatever the background mode does. An **unbounded background that
delivers stdout on exit is `pass`**, whether or not an option exists to name it.

How to decide, in order:

1. Read this host's tool/schema/docs for the background-command timeout
   parameter (name may be `timeout`, `timeout_ms`, `block_until_ms`, …).
2. If the documented maximum is `>= 3000` s, or unlimited/0, record `pass`.
3. If there is no such parameter, decide by the unbounded-background rows above.
4. If you are still unsure, submit a **short** background Python call
   (`python -c "raise SystemExit(0)"`) **with timeout requested at
   `>= 3000` s**. If the host **accepts** the call (does not reject the
   timeout argument), record `pass`. If it rejects or clamps below
   3000 s, record `fail`.
5. Kill that short process if it is still running. Do not leave it up.

`fail` does **not** block LWAR. It only forbids a 50-minute **background**
slice. Official ADP is still the blocking `exit-notify` loop below.

### 1b. Blocking cap (`host_blocking_cap_s`) — decides your slice length

Question: what is the longest a single **blocking** tool call may run on this
host before it is killed or forcibly detached?

Read the tool schema or docs and record a number in seconds, or `none` if
blocking calls are unbounded. Many hosts cap this at 600 s (10 minutes) even
though the ADP default slice is 3000 s.

Derive the slice you will actually pass:

```text
slice_s = 3000                              if host_blocking_cap_s is none
slice_s = max(60, host_blocking_cap_s - 60) otherwise
```

Use `slice_s` **everywhere** this bundle writes `--max-runtime-s 3000`:

```bash
python -u "<PAO_SKILL>/scripts/lwar.py" response REQUEST_ID --resident --max-runtime-s <slice_s>
python -u "<PAO_SKILL>/scripts/adp_exit_notify.py" --identity-file IDENTITY --max-runtime-s <slice_s>
```

A host that kills blocking calls at 600 s therefore uses `--max-runtime-s 540`.

**The protocol does not change — only the restart frequency.** The purpose is
that each slice ends with a normal `idle_timeout` (`reason=max_runtime`, exit
10) whose stdout this session reads, instead of a host kill that may discard it.
Shortening the slice is the official path on such a host, not a workaround; the
timeout recovery in [host-adapter.md](host-adapter.md) stays a compatibility
path for unexpected kills, not a loop to live in.

### 1c. Delivery on kill (`stdout_on_kill`)

Question: if this host **does** kill a call at its cap, does this session still
receive the stdout the process already produced?

Record `true`, `false`, or `unknown`. Treat `unknown` as `false`: with 1b
applied the kill should never happen, so an unproven answer costs nothing. If
you have evidence that a kill discards stdout, subtract a larger margin in 1b.

## 2. Notify style (`notify_style`)

```bash
python -u "<PAO_SKILL>/scripts/host_notify_probe.py"
```

Start that as a **background** tool if this host has a background tool.
The script prints `PAO_LIVE`, sleeps 5 seconds, then prints `PAO_EXIT`.

| What this session sees | `notify_style` |
|---|---|
| `PAO_LIVE` delivered **to this session, unprompted, before** the process exits | `live-notify` |
| Both lines **only after** exit, in this session / this turn | `exit-notify` |
| Exit output does **not** appear as this session's tool result (only a later panel, or never) | `exit-notify` + `blocking_required=true` |

**Delivery, not visibility.** `live-notify` means the host *wakes this session*
with each stdout line on its own. Output you can only obtain by **asking** —
calling a snapshot / "get command output" / `TaskOutput`-style tool, or any
agent-initiated poll — is **not** live-notify: record `exit-notify`. The
distinction matters because `adp_live_notify.py` never exits on its own; if the
host does not wake you, an event line is written and simply never handled, and
the task sits until its lease expires.

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

Exits on the first task/control/fatal or after the idle slice (`3000` s by
default, or the `slice_s` derived in 1b on a capped host — pass it as
`--max-runtime-s <slice_s>`). This session reads stdout, handles the event, then
starts the **same** script again. Fresh register still uses
`lwar.py response REQUEST_ID --resident --max-runtime-s <slice_s>`.

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
| any | `blocking_required=true` | **Blocking** `adp_exit_notify.py` with `--max-runtime-s <slice_s>`. Do not background. Do not wait for a new turn. |
| `fail` | `exit-notify` | Same blocking `adp_exit_notify.py` with `--max-runtime-s <slice_s>`. Do not start a 50-minute background slice. |
| `pass` | `exit-notify` | `adp_exit_notify.py`. Background start is allowed only if this session receives that child's stdout **on exit**. Prefer blocking. |
| `pass` | `live-notify` | `adp_live_notify.py` as a background tool with timeout >= 50 minutes (or unlimited). |

`slice_s` is 3000 unless 1b measured a blocking cap below it. A capped host runs
the same loop more often; nothing else differs.

Never start `adp_live_notify.py` unless `notify_style=live-notify` **and**
`bg_timeout_50m=pass`. Never wrap either watcher in a custom loop that
captures stdout (`capture_output=True`) — that hides both styles from
this session.

Keep the probe values (`bg_timeout_50m`, `host_blocking_cap_s`, `slice_s`,
`stdout_on_kill`, `notify_style`, `blocking_required`) in session memory. Do not
write them into mailbox paths, result `summary`/`evidence`, or artifact
contents. A diagnostic file the operator explicitly asked this session to write
is none of those and is allowed.
