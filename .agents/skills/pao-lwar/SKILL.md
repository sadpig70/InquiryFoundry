---
name: pao-lwar
description: "PAO LWAR (standalone, self-contained) — autonomously bootstrap, self-register, adopt an approved identity, and stay in the official ADP resident loop so OA mailbox send is the only later communication. Bundles the PAO runtime; installs by folder copy alone — no pip or plugin. Load on /pao-lwar or whenever a session is told to act as a PAO LWAR."
user-invocable: true
argument-hint: "start (agent action, not a CLI verb) | info | doctor | oa-status | register [number] | response --resident | adp | adp-exit | adp-live | adp-stop | adp-wait | status | on | drain | off | retire | unregister"
---

# PAO-LWAR Skill v1.18 (standalone)

Skill version (`v1.18`) and runtime protocol version (`1.4.2`, reported by
`pao.py info` / `doctor`) move independently. The **protocol** version is the
compatibility boundary — `register` stamps it and OA rejects a mismatch
fail-closed. The **skill** version tracks this document set. "Re-read a
reference if the runtime version changes" means the protocol version.

## Definitions

- **PAO** — Persistent Agent Orchestration: local orchestration of long-running AI runtimes over a file bus.
- **OA** — Orchestration Agent: approves registrations, publishes tasks, validates results.
- **LWAR** — Long-running Worker Agent Runtime: the stable execution identity (`LWAR1`, `LWAR2`, ...) that hides provider and model names.
- **ADP** — After the once-per-session host probe, this agent runs **exactly one** bundled watcher for its style. **exit-notify:** `scripts/adp_exit_notify.py` (`lwar.py adp` / `adp-exit`) — process exits on the first task/control or after 50 idle minutes; this session reads stdout, handles the event, restarts the same script. **live-notify:** `scripts/adp_live_notify.py` (`lwar.py adp-live`) — process stays up and emits each JSON line while running; handle `task_received` without killing it. Detect the style with [references/host-notify-probe.md](references/host-notify-probe.md) before the first watcher. After the operator's one-time `/pao-lwar`, later work arrives only via the OA mailbox. See [references/adp-loop.md](references/adp-loop.md).
- **TaskContract / ResultContract** — the task and result JSON payloads; schemas live in [schemas/](schemas/).

## 0. Self-Contained Invocation

This skill bundles the full PAO runtime (`scripts/`, `pao_runtime/`, `schemas/`). In every command, replace the placeholder `<PAO_SKILL>` with the **absolute path of the folder containing this SKILL.md**. It is a documentation placeholder, not an environment variable — never pass it to a shell unresolved, and always quote the substituted path. If this host's shell does **not** preserve quotes (some tool-driven shells pass them through as literal argument characters, splitting `--runtime-name "My Runtime"` into two arguments), use values without spaces or the host's own escaping instead — verify with one short command before `register`.

```bash
python "<PAO_SKILL>/scripts/lwar.py" register
```

Bus root resolution before identity adoption (`doctor`, `register`, `response`) is explicit `--root` > `PAO_ROOT` > a **`.pao/` folder under the current directory**. Adoption persists the canonical `bus_root` in the identity. Afterwards, `status`, `state`, `complete`, and ADP derive the bus from `--identity-file` when neither `--root` nor `PAO_ROOT` is supplied. An explicit/env root may repeat the identity root but a mismatch fails closed before touching the conflicting bus. `<root>/var/identities/<instance_id>.json` is the canonical location adoption writes to; an identity stored there derives its root from that path even if its record predates the stored `bus_root` field. That the location is canonical does **not** make its contents adoptable — see §0.5. Task execution still happens in each task's own `cwd`; only the bus location is identity-bound. The bus requires a **single-host local filesystem**. Run commands with the current runtime's Python executable — do not assume `python` and `python3` resolve to the same interpreter. Always invoke the wrapper scripts **through that interpreter** (`python "<PAO_SKILL>/scripts/lwar.py" …`), never by executing the file directly: their `#!/usr/bin/env python3` shebang is ignored on Windows and may select a different interpreter elsewhere.

Before registering or starting ADP, run the pre-flight check and stop on failure:

```bash
python "<PAO_SKILL>/scripts/pao.py" doctor --role lwar
```

Runtime protocol v1.4.2 intentionally rejects optional-first pre-v1 records
and pre-execution-fence bundles.
Use a fresh bus for the major-version cutover, or intentionally retire the old
bus after preserving required evidence. Never bypass a failed
`v1_bus_contract` doctor check by editing mailbox JSON.

### Default autonomous invocation

If the instruction is only "read this skill and act as a PAO LWAR", or
`/pao-lwar` is invoked with no action, treat that as an executable `start`
command. Do not summarize this skill, ask for a second bootstrap prompt, or wait
for the operator to restate the procedure. Resolve `<PAO_SKILL>` from this
`SKILL.md`, read the **required** reference set listed in §2 in full (the
conditional ones only when they apply to this runtime), execute
the Session Bootstrap (including the once-per-session host-notify probe), then
enter the style-selected ADP loop in §0.5 / Rule 3
(`adp_exit_notify.py` or `adp_live_notify.py`). Do **not**
end the turn waiting for host stdout-inject unless the probe selected
live-notify. After an exit-notify watcher exits, handle stdout and restart
that same script. The operator does not relay OA messages.

If a turn ends before the restart is issued, the ADP pauses — expected, not an
error. **Restart the watcher as the first action of your next turn**, before
answering whatever the operator asked, and do **not** re-bootstrap or
re-register: see "When the turn ends anyway" in
[references/adp-loop.md](references/adp-loop.md).

The files under this skill folder are the complete operating contract. No
repository README, external bootstrap guide, plugin, pip package, or vendor-
specific prompt is required. Environmental prerequisites are limited to the
current Python interpreter, one local bus selected by `--root`, `PAO_ROOT`, or
the `<cwd>/.pao` default. OA and LWAR may start in either order: an absent OA is
an observable wait state, not a bootstrap failure. If doctor fails, report the
exact event; do not replace execution with a tutorial.

## 0.5 Session Bootstrap (cold start)

**Register only if this session intends to do mailbox work.** The trigger is the
operator's instruction, not your own assessment of the situation:

- `/pao-lwar`, "act as a PAO LWAR", "register as LWARn", or any instruction to
  run/serve/join → **register.** This is the default. An absent, stale, or
  missing OA does not change it, and neither does having nothing to do yet:
  waiting for mailbox work *is* the job.
- "read this skill", "review it", "evaluate it", "diagnose the bus" → run
  `doctor`, the host probe, and `oa-status`, then **stop at step 5 without
  registering** and report. That is the correct outcome for such a session, not
  an incomplete bootstrap.

`register` takes a real numbered slot that only OA can return, and a slot held
by a session that will never watch its mailbox is indistinguishable, to OA, from
a runtime that failed to start. But the reverse failure is worse and quieter: a
session that was told to serve and silently declined to register leaves the
operator waiting for an LWAR that never appears. When the instruction is
ambiguous, register — an unwanted slot is one OA command to reclaim.

Run this decision flow at the start of a session, before any other action:

```text
1. Resolve <PAO_SKILL> from this file and resolve the pre-adoption bus by §0.
2. Build a truthful runtime profile from information already available to this
   session. Use register.md's explicit `unreported` sentinels for unavailable
   fields; do not ask for a second bootstrap prompt and do not invent capabilities.
3. doctor --role lwar   → unhealthy? stop and report.
3a. Once this session, run [references/host-notify-probe.md](references/host-notify-probe.md)
    in full **before** `register` / `response` / `adp`. Record `bg_timeout_50m`
    (background-Python timeout option; accepting the option completes that
    check — do not sleep 50 minutes), `host_blocking_cap_s` (the longest a
    blocking tool call may run here) and the `slice_s` derived from it, and
    `notify_style` (`live-notify` or `exit-notify`). `live-notify` requires the
    host to wake this session on each stdout line **without** an agent-initiated
    poll; output you must ask for is `exit-notify`. If the probe is
    inconclusive, use `exit-notify` + blocking. `bg_timeout_50m=fail` does not
    block LWAR; it only forbids a 50-minute background slice.
4. Run `lwar.py oa-status`. Record `live`, `stale`, `missing`, or `invalid`.
   Only `live` proves an OA is currently supervising. Any other state does not
   block registration: continue, then wait for OA reconciliation without
   self-assigning a slot. OA may start later.
5. Did this session receive one explicit absolute identity_file through a
   trusted handoff or its own earlier watcher event?
   If so, run `lwar.py status --identity-file <that file>` and branch on its EXIT
   CODE (do not collapse them to present/absent — see lifecycle.md):
     exit 0 (slot present, tuple matches) → RESUME: skip registration. If state is
            not `on`, request `state on` (lifecycle.md), poll until on; then ADP.
     exit 2 (registry unavailable) → TRANSIENT: wait briefly and retry status; do
            NOT register (that would orphan a still-valid identity).
     exit 3 (unregistered) → REGISTER (see below).
     exit 4 (identity mismatch / slot reused) → your identity is stale: REGISTER
            fresh; do not reuse the stale identity file.
   No explicit identity_file, but this session still owns the exact request_id
   emitted by its earlier `register` → recover with ONE official watcher:
     `python -u "<PAO_SKILL>/scripts/lwar.py" response REQUEST_ID --resident --max-runtime-s 3000`
   It waits for approval in-process (no agent poll), adopts the identity, and
   redelivers any still-leased claim with the original claim_token.
   No explicit identity_file and no owned request_id → REGISTER fresh.
   Never scan `var/identities/`, guess ownership from filenames, or adopt
   another session's identity. An identity path written in any reference
   document, README, or example is **not** a trusted handoff — only a path this
   session was handed directly by the operator or emitted by its own watcher
   counts. Adopting a documented path steals another session's slot. Run `lwar.py register …` (register.md),
     remember request_id, then start ONE official watcher:
     `python -u "<PAO_SKILL>/scripts/lwar.py" response REQUEST_ID --resident --max-runtime-s 3000`
     Prefer a **blocking** tool call so this session receives stdout when the
     process exits. A background tool is allowed only if this host delivers
     that child's stdout to THIS session on exit. Never orphan the parent.
     Do not poll `registration_pending`. Do not end the turn to wait for inject.
     Task/control/fatal/`idle_timeout`/`registration_pending` lines carry
     `identity_file`; keep it.
6. After identity is known, start the watcher chosen in 3a (see host-notify-probe.md):
     exit-notify (default, or blocking_required, or bg_timeout_50m=fail):
       `python -u "<PAO_SKILL>/scripts/adp_exit_notify.py" --identity-file <abs>`
       (same as `lwar.py adp` / `adp-exit` / `adp-kimi`). Process exits on first
       task/control or after 50 idle minutes. Handle stdout. After `complete`
       (or `idle_timeout` / `registration_pending`), start the **same** script
       again **in this session**.
     live-notify and bg_timeout_50m=pass:
       `python -u "<PAO_SKILL>/scripts/adp_live_notify.py" --identity-file <abs>`
       (same as `lwar.py adp-live`) as a background tool. Handle each stdout
       line while it runs. Do not kill it after `complete`. Do not start a
       second watcher.
   Do not wait for the operator. Do not restart on `shutdown` / successful
   `retire` / `adp_error`. Never start a second watcher while the first is
   alive. Do not file-poll.
```

Never re-register when a valid identity already exists — a needless re-registration
takes a new slot/generation and orphans the old one. All `--identity-file` and
`--result-file` arguments must be **absolute paths** (they resolve against the
process cwd, not the bus root).

`start` is the agent-level default action: it runs this bootstrap and ADP. It is
not a separate Python subcommand.

## 1. Absolute Rules

1. Before registering, read [references/register.md](references/register.md). Before the **first** watch slice, read [references/host-notify-probe.md](references/host-notify-probe.md) and [references/adp-loop.md](references/adp-loop.md) **in full** — the host style, exit-code contract, lease alignment, and stale-identity rejection are pre-loop knowledge, not lookup-on-event material. A host adapter must also read [references/host-adapter.md](references/host-adapter.md). If this runtime is Codex (`adapter_id=codex`), also read [references/codex-cli-adapter.md](references/codex-cli-adapter.md) **in full** before the first `adp` — Codex must use a blocking tool; it must not wait for a new turn. Read each reference in full once per session before its first use; re-read only if the file or the runtime version changes.
2. Use only the approved `(lwar_id, instance_id, generation)` as your runtime identity. Never claim an `LWARn` identity before approval.
3. **Run the watcher that matches the host-notify probe.** exit-notify (default): `adp_exit_notify.py` / `lwar.py adp`. Prefer a blocking `python -u` tool so stdout of the **exited** process lands in this session. After each exit: read JSON; if `task_received` then `begin` → work → `complete` **then** restart the same script; if `idle_timeout` / `registration_pending` then restart immediately. live-notify (only if probe `pass` + `live-notify`): `adp_live_notify.py` / `lwar.py adp-live` as a background tool; handle each stdout line while it runs; do not restart after `complete`. If `shutdown` / successful `retire` / `adp_error` then stop. Do not start `adp_live_notify.py` on any host whose probe returned `notify_style=exit-notify` (that includes an inconclusive probe). Do not file-poll. Do not wait for a human to paste OA text — the mailbox **is** OA's message. `--detach` / `adp-wait` / `kimi_adp_recycle.py` are not official. Never start a second watcher while the first is alive.
4. `idle_timeout` with `reason=max_runtime` (exit 10) is the official idle of `adp` / `--resident --max-runtime-s`: restart the same watcher. `idle_timeout` / `state_wait` without `--max-runtime-s` are compatibility single-slice events. `--background` `watcher_report` is informational only if you opted into that non-official path.
5. On `task_received`, preserve `invocation_id`, `execution_id`, and
   `task.claim_token`, then run `lwar.py begin` **before any task command,
   filesystem write, network call, or other side effect**. Execute only after
   `execution_began`; on `execution_fenced`, do not execute. For
   **exit-notify**, the watcher has already exited; restart `adp_exit_notify.py`
   only **after** `complete`. For **live-notify**, the watcher stays up; do
   not start another. Submit exactly one terminal result with `complete` and the granted
   `execution_token`. `complete` means terminal submission, not success —
   `failed`, `blocked`, `cancelled`, `timed_out`, and `protocol_error` outcomes
   are all submitted the same way. A crash or forced termination is recovered
   by lease expiry and OA `recover`; it is never inferred as success.
6. Session ADP terminates only on `shutdown`, successful `retire`, fatal `adp_error`, or the context-exhaustion handoff ([references/lifecycle.md](references/lifecycle.md)). Watcher **process** exit on the first event or `--max-runtime-s` is not session termination — restart unless the event was `shutdown` / successful `retire` / `adp_error`. For `retire`, stop only after `lwar.py retire` reports `lwar_retired`; `retire_waiting` means OA reconciliation is still required. For the handoff: only on an **objective** exhaustion signal (an explicit runtime context/token warning, not elapsed time or a feeling of being done), execute the procedure in [references/lifecycle.md](references/lifecycle.md). Never just stop.
   An OA may administratively retire an exact stale idle identity through the
   tuple-, heartbeat-observation-, age-, and empty-mailbox-fenced
   `recover --retire-stale` contract. Once that succeeds, the identity is
   permanently stale and must never resume or reuse its identity file.
7. Do not modify registry, incoming, or lease files by hand; act only through the bundled CLI.
8. Do not pollute context by restating idle stdout messages at length.
9. On an unknown watcher event, fail closed **on the event, not the daemon**: if a task is claimed, submit a `protocol_error` terminal result. Under live-notify, do not kill the running watcher; under exit-notify the process has already exited, so simply do not restart it until the event is resolved. Never retry the unknown event blindly. If the watcher process itself exits with an unknown code, treat that as `adp_error` and stop (do not auto-restart).
10. Never expose provider, vendor, or model names in result metadata, mailbox paths, artifact paths, or artifact contents — the `LWARn` alias is the only external identity. `complete` enforces this against the registered runtime profile.
11. Preserve the exact `task.claim_token` emitted by `task_received` and pass it to `complete`. A recovered/requeued claim has a new token; an old worker must fail closed instead of submitting into the new attempt.
12. Treat the adopted identity's `bus_root` as immutable authority. Never redirect that identity to another bus; a root conflict is a fatal configuration error.
13. Treat the owned registration `request_id` as the pre-identity recovery
    handle. If the watcher `response` process dies before adoption, start that
    exact command once more (`response --resident --max-runtime-s 3000`); do not register again.
    Restarting after `registration_pending` is **bounded**, not endless: if
    approval has not arrived after a wall-clock budget you set in advance
    (default: 1 hour, or 6 consecutive `registration_pending` restarts), stop
    restarting and report the exact `request_id`, `instance_id`, and the
    observed `oa-status` to the operator. A dormant bus is an operator problem,
    not something to wait out forever. Never re-register to escape the wait, and
    never delete your own pending request: an approved-but-unadopted slot and an
    unapproved request are both cleared by OA (`recover --reclaim-unadopted`),
    never by the LWAR. A
    `task_received` event with `recovered_claim: true` is the same durable
    claim and MUST retain its original `claim_token`.
14. A watcher invocation is an epoch-fenced delivery attempt, not execution
    authority. A newer replay supersedes older watcher output. Only `begin`
    grants execution authority, and only its `execution_token` may complete the
    claim. Never use tokenless legacy completion for a newly delivered task.

The atomic adoption command emits the one-time `starting` heartbeat and then
emits operational heartbeats from its in-process watcher; the agent never
writes them.

## 2. Action Routing

Before performing an action for the first time this session, read its reference document in full. Do not act from this table alone.

| Action | Read first |
|---|---|
| orientation — how OA and LWAR collaborate | **required** — [references/collaboration-principles.md](references/collaboration-principles.md) |
| `start` / no explicit action | the six **required** references marked here, then §0.5 |
| first-session timeout option + live-notify / exit-notify | **required** — [references/host-notify-probe.md](references/host-notify-probe.md) |
| `register [number]`, `response`, identity adoption | **required** — [references/register.md](references/register.md) |
| `adp` — the watch loop, stdout events, control commands | **required** — [references/adp-loop.md](references/adp-loop.md) |
| executing a claimed task, drafting and submitting results | **required** — [references/execute-complete.md](references/execute-complete.md) |
| `oa-status`, `status`, `on`, `drain`, `off`, `retire`, `unregister`, exhaustion handoff | **required** — [references/lifecycle.md](references/lifecycle.md) |
| host supervision, blocking-call timeout recovery | conditional — [references/host-adapter.md](references/host-adapter.md), when acting as a host adapter |
| background host start / 24h report | conditional — [references/background-playbook.md](references/background-playbook.md), live-notify hosts only |
| Kimi CLI (no stdout inject, 1h job) | conditional — [references/kimi-cli-adapter.md](references/kimi-cli-adapter.md), when `adapter_id` is `kimi_cli` |
| Codex CLI (no new-turn on TaskOutput) | conditional — [references/codex-cli-adapter.md](references/codex-cli-adapter.md), **required** when `adapter_id` is `codex` |

A conditional reference that does not match this runtime's `adapter_id` is not
required reading, and its host-specific instructions do not apply here.

### Canonical commands by `notify_style`

This table is the single source for **which command to run**. When any other
section, reference, or `scripts/README.md` appears to say otherwise, this table
wins. Resolve remaining disagreements in this order: **adapter constraint**
(a reference matching this runtime's `adapter_id`) > **host-notify probe result**
> **generic default**.

| Step | exit-notify (default) | live-notify (probe `live-notify` **and** `bg_timeout_50m=pass` only) |
|---|---|---|
| register | `lwar.py register …` | same |
| identity adoption | `lwar.py response REQUEST_ID --resident --max-runtime-s 3000` as a **blocking** call | `lwar.py response REQUEST_ID --background` |
| watcher | `scripts/adp_exit_notify.py --identity-file <abs>` (`lwar.py adp` / `adp-exit`) | `scripts/adp_live_notify.py --identity-file <abs>` (`lwar.py adp-live`) as a background tool |
| after `task_received` | `begin` → work → `complete`, **then restart the same script** | `begin` → work → `complete`; the process is still running — **do not restart it** |
| after `idle_timeout` / `registration_pending` | restart the same script immediately | not emitted; the process stays up |
| process lifetime | exits on the first event or `--max-runtime-s` | exits only on `shutdown` / successful `retire` / `adp_error` |
| watchers alive at once | exactly 1 | exactly 1 |

`--background`, `--detach`, `adp-wait`, and `kimi_adp_recycle.py` are never the
exit-notify path. A host whose probe was inconclusive is exit-notify.

`3000` is the default idle slice. On a host whose blocking calls are killed
sooner, pass the shorter `slice_s` derived in host-notify-probe.md §1b
(`--max-runtime-s <slice_s>`, e.g. `540` where the cap is 600 s) so each slice
ends with a readable `idle_timeout` instead of a host kill. Only the restart
frequency changes.

**Action name → actual CLI** (the hints are short labels; the CLI verbs differ):

| Hint / label | CLI command |
|---|---|
| `info` | `pao.py info` |
| `doctor` | `pao.py doctor --role lwar` |
| `oa-status` | `lwar.py oa-status` before adoption; add `--identity-file <abs>` after adoption |
| `register [number]` | `lwar.py register [number] --runtime-name … --model … --adapter-id … --vendor-family … --interface …` (register.md lists the required flags). `[number]` requests a **specific slot** (`register 5` → `LWAR5`); omit it and OA assigns the lowest available |
| `response` | exit-notify: `lwar.py response REQUEST_ID --resident --max-runtime-s 3000`. live-notify: `response REQUEST_ID --background` |
| `adp` / `adp-exit` / `adp-kimi` | `lwar.py adp --identity-file <abs>` or `scripts/adp_exit_notify.py` — exit on event or 50m |
| `adp-live` | `lwar.py adp-live --identity-file <abs>` or `scripts/adp_live_notify.py` — stay up, emit each event |
| `adp-stop` | `lwar.py adp-stop --identity-file <abs>` or `--request-id` or `--pid-file` (detach path only) |
| `adp-wait` | `lwar.py adp-wait --identity-file <abs>` — detach path only; not Kimi primary |
| `begin` | `lwar.py begin --identity-file <abs> --task-id … --claim-token … --execution-id … --invocation-id …` |
| `status` (this LWAR's own) | `lwar.py status --identity-file <abs>` (refreshes your identity state; use this, not `oa.py status`, for self-inspection) |
| `on` / `drain` / `off` | `lwar.py state on` / `lwar.py state draining` / `lwar.py state off` |
| `retire` | repeatedly run `lwar.py retire --identity-file <abs>` until `lwar_retired`; OA reconciles each requested transition |
| `unregister` | `lwar.py state deregistered` (only from `off`, after OA reconcile) |

Every LWAR-side exit code is collected in one table in
[references/lifecycle.md](references/lifecycle.md) ("Exit code dictionary").
Branch on the stdout JSON `event`; treat the code as corroboration.

`conformance/` is an OA-side calibration pack (`factory.conformance.v1`): probe
task templates a Factory verifier publishes to measure model adherence. An LWAR
never reads, publishes, or self-runs it, and its `.task.json` templates are not
TaskContracts — a real task arrives only through the mailbox.

`PAO_LWAR_IDENTITY` may hold the absolute identity path as a fallback for the
ADP scripts when `--identity-file` is omitted. Prefer the explicit flag; the
environment variable is convenience, not a second source of identity.

JSON Schemas for every bus message live in [schemas/](schemas/). The ones an
LWAR meets directly are `registration-request` / `registration-response`,
`identity`, `heartbeat`, `invocation`, `lease`, `execution`, `task`, `control`,
`adp-event`, `result`, and `lifecycle-request` / `lifecycle-response`; the rest
(`registry-state`, `tombstones`, `task-ledger`, `validation-decision`,
`oa-presence`, `oa-writer-lease`, `audit-event`, and the routing/canary set)
belong to OA and are validated on its side of the bus.
The runtime validates them at every registration, lifecycle, mailbox, heartbeat,
lease, task, control, result, and identity trust boundary.
