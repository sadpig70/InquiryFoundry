# LWAR Reference — Registration and Identity Adoption

Replace `<PAO_SKILL>` with this skill's folder (SKILL.md §0). Before registering,
run the Session Bootstrap flow (SKILL.md §0.5). Resume only an identity whose
absolute file path was explicitly handed to this session or produced by this
session's own watcher event. Never scan `var/identities/` or guess
ownership; without a trusted handle, register a fresh identity.

## Registration

First inspect OA presence without requiring an identity:

```bash
python "<PAO_SKILL>/scripts/lwar.py" oa-status
```

Exit `0` means `live`; exit `2` means `missing` or `stale`; exit `3` means an
invalid presence record. Only `live` proves an OA is currently supervising.
Registration remains order-independent: when OA is unavailable, publish the
registration request normally and wait. Never infer approval or self-assign a
slot.

Use your OWN actual runtime metadata — the example below is illustrative
(Codex/OpenAI), not a template to copy. Fill each flag with the truth about the
session you are:

| Flag | What to put | Autonomous fallback if unavailable |
|---|---|---|
| `--runtime-name` | the harness/CLI you run in (e.g. "Claude Code", "Kimi Code CLI") | `Unreported Runtime` |
| `--model` | your model name (e.g. "Claude Fable 5") | `Unreported Model` |
| `--adapter-id` | a lowercase slug for the runtime (e.g. `claude_code`) | derive from runtime-name; otherwise `unreported_runtime` |
| `--vendor-family` | lowercase vendor slug (e.g. `anthropic`, `moonshot`) | `unreported_vendor` |
| `--interface` | one of `cli` \| `tui` \| `agent` \| `build` | `agent` for an agentic CLI |
| `--capability` | repeatable; what you can do (e.g. `coding`, `testing`) | omit if none apply |

Introspect metadata already exposed by the runtime/session first. Do not invent a
specific identity you cannot attest: the explicit `Unreported ...` / `unreported_*`
sentinels are truthful epistemic states and preserve autonomous bootstrap. Omit
capabilities you cannot verify. Never claim a guessed vendor, model, capability,
or adapter because that corrupts downstream routing.

```bash
python "<PAO_SKILL>/scripts/lwar.py" register \
  --runtime-name "Codex" \
  --model "GPT 5.5 Sol" \
  --adapter-id codex \
  --vendor-family openai \
  --interface cli \
  --capability coding \
  --capability testing
```

To request a specific slot, use `register 5`. If omitted, OA assigns the lowest available number.

The request is stamped with the bundle's `runtime_version` automatically; OA rejects a mismatched runtime fail-closed (`runtime_version_mismatch`), so both sides must run the same bundle version.

Remember the `request_id` returned on stdout.

## Identity adoption

Start adoption as **one background process** (host stdout-notify, `python -u`):

```bash
python -u "<PAO_SKILL>/scripts/lwar.py" response REQUEST_ID --background --report-every 86400
```

The process stays silent while OA has not written a response. After approval it
adopts the identity, emits one `identity_adopted` line, and keeps watching.
Do not poll `registration_pending` in the agent turn.

| stdout `event` | Meaning |
|---|---|
| `identity_adopted` | Slot approved; watcher is running. Remember `identity_file` |
| `task_received` | Mailbox work. Use the event's `identity_file` |
| `control` | OA control. `shutdown`/`retire` then exit the process |
| `watcher_report` | 24h pulse. Watcher still running |
| `registration_rejected` | Fail closed: inspect `reason`, do not retry the same request |
| `adp_error` | Adoption or the watcher failed; stop and report |

- Official start is `response REQUEST_ID --resident --max-runtime-s 3000`.
  Both `--resident` and `--background` wait in-process for OA approval.
  If the resident cap elapses first it emits `registration_pending`
  (`reason=max_runtime`, exit 2); restart the same `response` command.
  After approval `--resident` emits `identity_adopted` and exits on the
  first task/control/fatal or the remaining cap (`idle_timeout`).
- `--background` does not emit `registration_pending` while waiting. It is
  not the official path.
- `missing`/`stale`/`invalid` OA presence is not rejection; the process keeps waiting.
- Preserve the exact `request_id` before starting the watcher. If that
  process dies before adoption, start the same `response` command once more
  against the same bus root. It never creates a new registration or generation.
- Plain `response REQUEST_ID` (no flag) still emits `identity_adopted` and
  returns — diagnostic only.
- Never self-assign an `LWARn` before approval, and never accept a stale identity.
- After adoption, identity-bearing commands self-locate the bus from the identity file. If `--root` or `PAO_ROOT` is also supplied, it must resolve to the same canonical root or the command fails closed.
