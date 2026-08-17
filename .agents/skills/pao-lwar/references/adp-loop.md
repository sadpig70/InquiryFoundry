# LWAR Reference — ADP Watch Loop Contract

Replace `<PAO_SKILL>` with this skill's folder (SKILL.md §0). Read this document in full before the first watch slice.

Official ADP is the same on every host. The operator starts this session once
(`/pao-lwar`). After that, OA speaks only through the mailbox. This agent
must keep the resident loop running so it sees those files.

Before the first watcher, finish [host-notify-probe.md](host-notify-probe.md).
`bg_timeout_50m=pass` means only that this host **accepts** a background
Python timeout of >= 50 minutes — not that you waited 50 minutes.

Then run **one** bundled watcher:

```bash
# exit-notify (default; Codex/Kimi; blocking_required)
python -u "<PAO_SKILL>/scripts/adp_exit_notify.py" --identity-file IDENTITY

# live-notify only if probe is live-notify + bg_timeout_50m=pass
python -u "<PAO_SKILL>/scripts/adp_live_notify.py" --identity-file IDENTITY
```

`lwar.py adp` / `adp-exit` are aliases of the exit-notify script.
`lwar.py adp-live` is the live-notify script.

Fresh:

```bash
python -u "<PAO_SKILL>/scripts/lwar.py" response REQUEST_ID \
  --resident --max-runtime-s 3000
```

Resume:

```bash
python -u "<PAO_SKILL>/scripts/lwar.py" adp --identity-file IDENTITY
```

Prefer a **blocking** tool call. The process waits for OA approval (fresh
`response` only), then **exits** on the first task/control/fatal or after
`--max-runtime-s` (`idle_timeout`, exit 10). This session reads that stdout.
`complete` first, then restart the same command **without waiting for a
human**. Do not restart on `shutdown` / successful `retire` / `adp_error`.
Do not file-poll. Do not start `--background` and end the turn.

`--background` with host stdout-inject is a non-official Claude bonus only.

## Core loop — exit-notify (default, every host unless the probe says otherwise)

```python
def ADP_slice(identity_or_request) -> None:
    # Blocking call in THIS turn. The process exits; this session reads its stdout.
    lines = run_blocking(
        'python -u "<PAO_SKILL>/scripts/adp_exit_notify.py" --identity-file IDENTITY'
        # pre-adoption: lwar.py response REQUEST_ID --resident --max-runtime-s 3000
    )
    ADP_on_exit(lines)

def ADP_on_exit(lines) -> None:
    # Every line matters, but the LAST event decides the restart policy: the
    # adopting process keeps watching after `identity_adopted` and exits later.
    for line in lines:
        if line.event == "identity_adopted":
            remember(line.identity_file)
    event = lines[-1]
    if event.event == "identity_adopted":
        return ADP_slice(event.identity_file)   # adoption was the terminal line
    if event.event in ("idle_timeout", "registration_pending"):
        return ADP_slice(...)                   # restart the same command immediately
    if event.event == "adp_error":
        report_error_and_stop(event)
        return
    if event.event == "control":
        if event.command == "retire":
            submit_terminal_result_if_holding_a_claim()
            while run_lwar_retire(identity_file) != "lwar_retired":
                observe_oa_status(identity_file)
            return                              # do not restart
        if event.command == "shutdown":
            submit_terminal_result_if_holding_a_claim()
            return                              # do not restart
        handle_control(event)
        return ADP_slice(...)                   # ping / drain / cancel: restart
    if event.event == "task_received":
        grant = run_lwar_begin(...)
        if grant.event == "execution_fenced":
            return ADP_slice(...)
        result = AI_execute_task(event.task)
        write_result_draft(result)
        run_lwar_complete(...)                  # complete FIRST
        return ADP_slice(...)                   # then restart the same script
    if holding_a_claim():
        submit_protocol_error_result()

    # acceptance_criteria:
    #   - exactly one watcher process is alive at a time, and zero while the agent works
    #   - the restart happens only after `complete`, never before
    #   - a process exit is normal, not a failure; only shutdown / successful retire /
    #     adp_error stop the loop
    #   - the agent re-invokes in the same turn and never ends the turn waiting for inject
```

## Core loop — live-notify / `--background` hosts only

Use this shape **only** when the probe returned `notify_style=live-notify` and
`bg_timeout_50m=pass`. On an exit-notify host it is wrong: following it either
skips the restart (the ADP stops) or leaves two watchers alive.

```python
def ADP_start(identity_or_request) -> None:
    # Host background process. Agent does not wait.
    start_background(
        'python -u "<PAO_SKILL>/scripts/lwar.py" response REQUEST_ID --background'
        # or adp_watch.py --identity-file ... --background --report-every 86400
    )
    end_turn()

def ADP_on_stdout_line(event) -> None:
    if event.event == "identity_adopted":
        remember(event.identity_file)
        return                                  # watcher already running
    if event.event == "watcher_report":
        return                                  # 24h pulse; do not restart
    if event.event == "adp_error":
        report_error_and_stop(event)
        return
    if event.event == "control":
        if event.command == "retire":
            submit_terminal_result_if_holding_a_claim()
            while run_lwar_retire(identity_file) != "lwar_retired":
                observe_oa_status(identity_file)
            return
        if event.command == "shutdown":
            submit_terminal_result_if_holding_a_claim()
            return                              # watcher process is exiting
        handle_control(event)
        return                                  # watcher keeps running
    if event.event == "task_received":
        grant = run_lwar_begin(...)
        if grant.event == "execution_fenced":
            return
        result = AI_execute_task(event.task)
        write_result_draft(result)
        run_lwar_complete(...)
        return                                  # watcher keeps running; no re-invoke
    if holding_a_claim():
        submit_protocol_error_result()

    # acceptance_criteria:
    #   - one background process owns heartbeat and mailbox polling
    #   - the agent never loops adp_watch in a single turn
    #   - stdout is silent except task/control/fatal/identity_adopted/watcher_report
    #   - watcher_report default period is 86400 seconds
    #   - after task delivery the process stays up and does not claim a second task
    #   - process exits only on shutdown, retire, or adp_error
```

`--timeout` remains the internal slice/heartbeat checkpoint; in `--background`
it never returns `idle_timeout`. `control:ping` is acked without a stdout line
so the agent is not woken. A `watcher_report` line is emitted every
`--report-every` seconds (default 24h) so the host can prove the process is
still supervised without per-poll agent turns.

The adopted identity stores its canonical `bus_root`, so this identity-only
invocation is safe even when the bus is not `<cwd>/.pao`. A supplied `--root` or
`PAO_ROOT` must match the identity; a mismatch emits fatal `adp_error` without
touching the conflicting bus. Legacy identities still self-locate when stored at
their canonical `<root>/var/identities/` path.

## Exit codes and stdout events

The agent must inspect both the exit code and the stdout JSON `event`. The two
watcher styles produce different codes for the same event, so read the column
that matches the style selected by the probe.

**The exit code your host reports is not always the process's exit code.** Some
tool wrappers collapse every non-zero status to `1`, or report the wrapper's own
result instead of the child's. The codes below are what the watcher process
returns. **Branch on the stdout JSON `event`**; use the reported code only as
corroboration, and if the two disagree, the JSON wins. If you need the true
code on such a host, read it from inside the call (for example a `python`
wrapper that reports `returncode`) rather than trusting the tool result.

| `event` | exit-notify | live-notify | Immediate action |
|---|---:|---:|---|
| `identity_adopted` | (process continues) | (running) | Remember `identity_file`. The adopting process keeps watching in-process under both styles — do not start another. Under exit-notify it exits later, on the first task/control/fatal or the remaining cap; that later event decides the restart |
| `task_received` | `0` then exit | (running) | Save all fence handles, run `begin`, execute only after `execution_began`. exit-notify: restart the same script **after** `complete`. live-notify: do not restart |
| `watcher_report` | n/a | (running) | 24h (or `--report-every`) pulse. Acknowledge. Do not restart the watcher |
| `idle_timeout` (`reason=max_runtime`) | `10` | n/a | Official exit-notify idle of `adp` / `--resident --max-runtime-s`. Restart the same watcher |
| `idle_timeout`, `state_wait` | `10` | n/a | Compatibility single-slice only (neither `--background` nor `--resident`+`--max-runtime-s`) |
| `registration_pending` (`reason=max_runtime`) | `2` | n/a | Approval has not arrived yet. Restart the same `response` command |
| `control:ping` | `20` then exit | (running, no stdout) | exit-notify: the ack is already written; restart. live-notify: acked with no stdout — if you somehow see this, ignore |
| `control:drain` | `20` then exit | (running) | Finish current work, request lifecycle `draining`. exit-notify: restart and keep serving until `shutdown`. live-notify: leave the watcher running until `shutdown` |
| `control:cancel` | `20` then exit | (running) | Stop the held task and submit `cancelled`, then restart (exit-notify only). Unclaimed cancels are tombstoned by the watcher |
| `control:retire` | `20` then exit | `20` then exit | Submit any held terminal result, then `lwar.py retire` until `lwar_retired`. The watcher process exits. Do not restart |
| `control:shutdown` | `20` then exit | `20` then exit | Submit held claim first (`interrupted` if no verdict). Watcher process exits. Do not restart |
| `adp_error` | `30` | `30` | Report, stop ADP. Do not auto-restart |
| `invocation_superseded` | `40` | `40` | This watcher lost to a newer replay; stop this invocation without executing |
| any unknown event | any other | any other | Fail closed on the **event**: if a task is claimed, submit `protocol_error`. Do not restart until it is resolved; under live-notify leave the running process alone |

Every watcher event includes the absolute `identity_file`. Heartbeats are written
by the watcher itself on every poll—the agent never emits or edits them.

One stdout line per event, shaped like these (fields trimmed to the ones you
act on; `adp-event.schema.json` is authoritative):

```json
{"event":"identity_adopted","identity_file":"D:\\...\\var\\identities\\lwar-instance-….json","lwar_id":"LWAR3"}
{"event":"task_received","identity_file":"…","invocation_id":"invocation-…","invocation_epoch":7,
 "task":{"task_id":"task-…","claim_token":"claim-…","execution_id":"execution-…","cwd":"…","timeout_s":300}}
{"event":"control","command":"shutdown","identity_file":"…","message":{"control_id":"control-…"}}
{"event":"idle_timeout","reason":"max_runtime","identity_file":"…"}
{"event":"registration_pending","request_id":"lwar-reg-…","reason":"max_runtime","action":"restart_response"}
{"event":"adp_error","error":"…","identity_file":"…","action":"stop"}
```

The fence handles you must carry from `task_received` into `begin` are
`task.claim_token`, `task.execution_id`, and `invocation_id`. A
`recovered_claim: true` field means the same durable claim is being redelivered
— keep the original `claim_token`.

Error discipline. `adp_error` (exit 30) means the watcher itself hit a fatal condition (e.g. the identity no longer verifies) and exited: **stop this ADP run and report** — do not blindly re-invoke the same command. The only case for a bounded retry is a *transient* error you have reason to believe is self-clearing (e.g. a momentary file lock); if you choose to retry, cap it at **3 consecutive identical `adp_error`s**, then stop and escalate to OA. Never loop on an unresolved error.

Cancel reaching an agent mid-execution. Under **live-notify** the watcher keeps
running while you execute, so `control:cancel` arrives as a host-injected stdout
line: stop the task and submit a `cancelled` result. Do not start a second
watcher to look for cancel. Under **exit-notify** the watcher has already exited
and must not be restarted before `complete`, so a cancel cannot reach a task
that is already executing — it is delivered on the next slice, after `complete`,
as `control:cancel` or through the tombstone. The upper bound on cancellation
delay is therefore that task's own execution time; this is a known limit of the
style, not a fault. (A cancel for a task you have not yet claimed needs no agent
action — the tombstone handles it, see below.)

When the slot is expected to stay in a non-`on` state for a while (e.g. `draining` wind-down), pass `--state-wait-backoff-max SECONDS` so the in-slice poll interval doubles up to that cap instead of busy-polling at `--interval`; it resets automatically when the state returns to `on`.

## Mailbox layout

```text
mailbox/LWARn/
    incoming/          # OA task publish area
    claimed/           # task atomically claimed by ADP
    outgoing/          # LWAR result publish area
    control/           # OA control publish area
    control_claimed/   # transient watcher claim area
    cancelled/         # cancel tombstones ({task_id}.json)
    leases/            # execution leases
    executions/        # execution records ({execution_id} fence state)
    work/              # LWAR working files, per task_id
    heartbeat.json     # written by the watcher only
    invocation.json    # current watcher invocation epoch
    watcher.pid.json   # present while a watcher process owns this mailbox
    archive/  failed/  dead/  quarantine/
```

The watcher owns `heartbeat.json`, `invocation.json`, `watcher.pid.json`,
`executions/`, and the atomic moves between the queue directories. The agent
writes only under `work/{task_id}/` and reaches everything else through the CLI.

All writes use temporary file → flush/fsync → `os.replace`. Task receipt is finalized by the atomic move `incoming → claimed`.

## Lease alignment

When a task is claimed, the watcher extends the lease to cover the task's own execution budget: `effective_lease_s = max(--lease-seconds, timeout_s + 30)`. Long tasks keep their lease for the whole declared window.

## Failure recovery

- The `--background` watcher does not exit on idle or after delivering a task. If it
  exits after a non-terminal control other than shutdown/retire, that is a bug:
  report it; do not write a turn-loop wrapper. **The exit-notify watcher
  (`adp` / `--resident --max-runtime-s`) is supposed to exit** after one event or
  50 idle minutes — restart after `complete` / `idle_timeout`.
- If a compatibility `--resident` blocking call times out and discards stdout,
  prefer restarting as `--background`. A new background watcher redelivers this
  identity's one unexpired leased claim as `task_received` with
  `recovered_claim: true`, preserving the original `claim_token`. Expired or
  multiple claims are not guessed; OA recovery remains authoritative.
- Every watcher entry creates a monotonic identity-bound invocation epoch.
  Delivery is serialized with epoch supersession, so a delayed orphan emits
  `invocation_superseded` instead of task/control data after a newer replay.
  Because stdout may already have reached more than one host context, the agent
  must still call `begin`: only the current invocation can atomically acquire
  the claim's stable `execution_id`, and all losing contexts must not execute.
- A `starting` heartbeat older than 30 seconds means the atomic in-process
  watcher entry failed or stalled; report `adp_error` evidence rather than
  treating agent latency as an acceptable cause.
- If the LWAR session dies, the heartbeat goes stale; OA `recover` returns expired-lease tasks to `incoming`.
- If a result already exists for the same `task_id`, do not auto-approve a replayed execution; OA `collect` quarantines duplicate and stale-generation results.
- Even when a numeric slot is reused, messages with mismatched `generation` or `instance_id` must be rejected.

## Cancel tombstones

Cancelling a task that has not been claimed yet is deterministic and no longer depends on agent memory across watch slices:

- When the watcher claims a `cancel` control carrying a `task_id`, it writes a tombstone at `mailbox/LWARn/cancelled/{task_id}.json` **before** the `control:cancel` event is returned to the agent.
- On any later claim, a task whose `task_id` is tombstoned is not handed to the agent. The watcher submits a terminal `cancelled` result through the normal pipeline — `attempt` and `claim_token` echoed from the claimed task, the summary naming the tombstone — consumes the tombstone, and keeps scanning. No new agent-visible event is emitted; the agent contract is unchanged.
- The tombstone makes the not-yet-claimed cancel race-free even if the cancel control and the task publish arrive in either order. Duplicate cancels are first-writer-wins, and a tombstone for an already-completed (or never-arriving) task is simply never consumed — both are harmless. The `control:cancel` event still reaches the agent so it can stop a task it is already executing.
