# Host Adapter Supervision Contract

This contract applies when a host runtime wraps PAO commands in tool calls that
may impose a maximum blocking duration shorter than the resident ADP lifetime.
A host timeout is an interruption of result delivery, not proof that the LWAR,
identity, claim, or task failed.

## Capability fence

Prompt instructions are not enforcement. Before a provider run that requires
zero tools or exact token telemetry, the host adapter MUST prove both properties
at its process boundary. The bundled Qwen supervisor provides that boundary:

```bash
python "<PAO_SKILL>/scripts/host_adapter.py" qwen-probe --live
python "<PAO_SKILL>/scripts/host_adapter.py" qwen-run \
  --task-file task.json \
  --prompt-file prompt.txt \
  --receipt-file receipt.json
```

The live probe is eligible only when Qwen supports `--bare`,
`--output-format json`, `--max-tool-calls 0`, and `--max-wall-time`, then
actually returns zero tool calls, exact input/output/total tokens, and at most
one provider call. A static probe without `--live` is intentionally ineligible.

`qwen-run` requires this exact TaskContract extension:

```json
{
  "adapter_options": {
    "host_contract": {
      "adapter_id": "qwen_code",
      "tool_policy": "deny_all",
      "token_telemetry": "exact_provider_report",
      "max_provider_calls": 1
    }
  }
}
```

The supervisor always adds `--bare --output-format json --max-tool-calls 0`,
checks provider-call and token totals against the terminal statistics, and
writes a `pao.host-execution-receipt.v1`. Missing telemetry, any tool call, a
second provider call, malformed output, timeout, non-zero exit, or task-contract
drift writes a rejected receipt and exits 4. Only an accepted receipt may feed
calibration or routing evidence.

## Blind-safe receipt evidence

A host receipt identifies its own adapter (`adapter_id`, `model_ids`,
`runtime_version`) — those are the LWAR's registered identity terms, and
`lwar.py complete` fails closed if any of them appear in `summary` or `evidence`
(`result metadata exposes runtime identity terms: ...`). This keeps blind
evaluation blind, so a calibration task must NOT ask the LWAR to submit the full
receipt. Instruct it to submit only the blind-safe subset:

- `status`, `reason_codes`
- `tool_calls`
- `usage` (`input_tokens` / `output_tokens` / `total_tokens`)
- `output` (the provider answer)
- `session_id`, `raw_output_sha256`, `host_contract_sha256`

Drop `adapter_id`, `model_ids`, and `runtime_version`, and never restate the
runtime name, model, or vendor in `summary`/`evidence`. The dropped fields carry
no gate signal — acceptance rests on `status == accepted`, `tool_calls == 0`,
and exact `usage`, all of which are identity-free.

## Kimi Code CLI adapter

A second supervisor enforces the same `deny_all` / `exact_provider_report`
contract for the Kimi Code CLI (`adapter_id: kimi_cli`, vendor `moonshot`,
model `kimi-code/kimi-for-coding`):

```bash
python "<PAO_SKILL>/scripts/host_adapter.py" kimi-probe --live
python "<PAO_SKILL>/scripts/host_adapter.py" kimi-run \
  --task-file task.json --prompt-file prompt.txt --receipt-file receipt.json
```

The task `host_contract` is identical except `adapter_id` is `kimi_cli`. The
supervisor always runs
`--print --output-format stream-json --max-steps-per-turn 1 --model kimi-code/kimi-for-coding`.
Tool discipline is structural: one step per turn cannot both call a tool and
emit a final answer, and any assistant non-text tool part or tool-role stream
event additionally rejects as `tool_call_observed`. Token telemetry is read only
from the current session's exported `wire.jsonl` (`kimi export SESSION --yes`):
the latest non-empty `StatusUpdate.token_usage` is folded into
input/output/total, where every component must be a non-negative integer whose
key starts with `input` or `output` (an unclassifiable key fails closed).

Static flag discovery runs the `--help`/`--version` probe with `COLUMNS=200`
because Kimi renders help in a bordered table that otherwise truncates long
flag names (`--max-steps-per-turn` -> `--max-steps-per`) and defeats a naive
substring check.

Two adapter-scoped limitations are recorded honestly and must be confirmed
before the limitation matters:

1. **No provider-call count.** Kimi `token_usage` exposes no per-call request
   count, so the receipt omits `provider_calls`; `max_provider_calls=1` is
   enforced structurally by the single turn, not observed from telemetry.
2. **Tool-signal token set is an assumption.** Tool detection matches content
   part types / event roles containing `tool` or `function`. A live probe on
   Kimi 1.38.0 (a finite ordering task) confirmed the assistant emits only
   `text` and `think` content parts and solves natively with zero tools, so
   reasoning (`think`) parts are correctly not misread as tools. An actual
   Kimi tool-use part type name remains unobserved; `--max-steps-per-turn 1`
   structurally prevents a tool round-trip and a final answer in one turn.

## Host capability matrix

Measured values from runtimes that have executed this bundle's bootstrap. Use
your own row if it exists, **verify it** with [host-notify-probe.md](host-notify-probe.md)
anyway (a host can change), and add a row when your runtime is missing. This
table replaces per-vendor adapter documents for everything except the two
supervisors above and the Codex delivery rule.

| Runtime (`adapter_id`) | `notify_style` | Blocking cap | Background timeout | Host-specific caution |
|---|---|---:|---|---|
| Claude Code (`claude_code`) | exit-notify | 600 s | unbounded; stdout on exit | Running output is visible only by polling — that is not live-notify |
| Codex (`codex`) | exit-notify | unmeasured | unmeasured | A background `TaskOutput` does **not** wake the session; blocking required |
| DeepSeek TUI (`deepseek_tui`) | exit-notify | 600 s | 600 s | Shell does not preserve quotes — avoid spaces in argument values |
| Antigravity (`antigravity`) | exit-notify | ~10 s then auto-async | no option; unbounded | Wakes the session when the background task completes |
| opencode / GLM | exit-notify | blocking only (no background tool) | n/a | Accepts large timeout arguments; survival at that length unverified |
| Grok Build TUI (`grok_build`) | exit-notify | 120 s default → auto-background; max 10 h | `timeout:0` = unlimited | Timeout kill takes children with it; host-reported exit code differed from the real one |
| Kimi Code CLI (`kimi_cli`) | exit-notify | ~1 h job limit | unmeasured | No live stdout inject |
| Qwen Code (`qwen_code`) | exit-notify | 600 s | no option; unbounded + completion notify | A streaming `monitor`-style tool that kills idle processes after 5–10 min must not carry ADP |

Two conclusions this table already supports:

1. **No runtime here is live-notify.** Treat `adp_live_notify.py` as the
   exception that must be earned by a probe, never as a starting assumption.
2. **A 600 s blocking cap is common.** Those hosts run the official loop with
   the shorter `slice_s` from host-notify-probe.md §1b; they are not excluded
   from the official path.

### Profile slugs

`--adapter-id` is a stable lowercase slug for the runtime, not the model:
`claude_code`, `codex`, `kimi_cli`, `qwen_code`, `deepseek_tui`, `grok_build`,
`antigravity`. Reuse the slug in this table if your runtime appears; otherwise
mint `<runtime>_<surface>` and add the row. Do not encode the model version.

`--interface` describes the surface this session runs on: `cli` (non-interactive
command), `tui` (interactive terminal UI), `agent` (agentic runtime that plans
and calls tools on its own), `build` (a build/CI-driven invocation with no
interactive operator). When a runtime is both a TUI and agentic, `agent` is the
routing-relevant truth.

Report only what you can verify. `register.md`'s `unreported` sentinels are more
useful than a guess.

## Durable handles

Official ADP after the host-notify probe is one of two bundled watchers:
`adp_exit_notify.py` (exit on event or 50 m) or `adp_live_notify.py`
(stay up, emit each line). Safe default is blocking `adp_exit_notify.py`.
Before the first watcher, run [host-notify-probe.md](host-notify-probe.md).
See [kimi-cli-adapter.md](kimi-cli-adapter.md) and [adp-loop.md](adp-loop.md).

`--background` plus live line inject is optional. If the host cannot keep the
parent attached (Codex orphan) or cannot inject lines (Kimi), do not use it.

`--resident` without `--max-runtime-s` remains a compatibility blocking call
until the first event. Those hosts follow the timeout recovery below.

Before invoking `lwar.py response REQUEST_ID --resident` (or the live-notify-only `--background`), the adapter MUST retain:

- the exact registration `request_id` emitted by its own `register` call
- the exact explicit bus root, or the unchanged environment/cwd that resolves it
- the resident timing arguments it supplied

The `request_id` is the only pre-identity recovery handle. After any watcher
event is received, the event's absolute `identity_file` becomes the normal
identity handle. The adapter MUST NOT scan `var/identities/`, infer ownership
from filenames, or register again merely because a blocking call timed out.

## Timeout recovery

On a host-enforced timeout that discards **resident** stdout (compatibility path
only; background mode should not hit this):

1. Do not interpret the timeout as task failure or submit a result.
2. Re-run the exact `lwar.py response REQUEST_ID --resident` command against the
   same bus root. Prefer restarting as `--background` if the host can.
3. Let response replay reconstruct and verify the exact
   `(lwar_id, instance_id, generation)` identity.
4. Let ADP inspect only that identity's mailbox. If one unexpired leased claim
   exists, ADP emits it again as `task_received` with
   `recovered_claim: true`.
5. Call `lwar.py begin` with the event's `claim_token`, stable `execution_id`,
   and new `invocation_id`.
6. Execute only on `execution_began`. On `execution_fenced`, do not execute;
   another context already owns the claim.
7. Complete with both the unchanged `claim_token` and the granted
   `execution_token`.

The watcher checks a resumable claim before accepting new work. It does not
extend the lease, rotate the token, or manufacture a TaskContract. An expired
claim is left to OA `recover`; multiple active claims fail closed as ambiguous.
The final `complete` command remains fenced against any concurrent OA recovery,
so a superseded token cannot publish a second terminal result.

## Acceptance criteria

- replay never registers a new LWAR or increments generation
- replay reconstructs only the identity bound to the owned request id
- one live claim is redelivered with byte-identical `claim_token`
- every replay has a higher invocation epoch but the same stable `execution_id`
- delayed old invocations cannot begin after replay supersession
- concurrent/replayed begin calls expose only one execution token
- new tasks are not claimed while a resumable claim exists
- expired, mismatched, or ambiguous claims are never adopted speculatively
- capability discovery without a live probe is never execution-eligible
- any tool call or missing/inconsistent token telemetry rejects the host receipt
- exactly one terminal result reaches OA collection
