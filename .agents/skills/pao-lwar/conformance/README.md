# Conformance pack — OA-side calibration, not LWAR work

This folder is a `factory.conformance.v1` calibration pack. It measures one
axis, `model_adherence`: whether a runtime driven through the PAO contract does
what it was told, reports honestly, and survives the ADP loop.

**An LWAR never reads, publishes, or runs this pack.** The `.task.json` files
here are *templates* held by a Factory verifier on the OA side, which
instantiates them (they carry placeholders such as `{{cwd}}`) and publishes the
result through the normal mailbox. A real task always arrives as a
`task_received` event — never as a file you found in the skill bundle. If you
are an LWAR reading this, there is nothing here for you to do.

## Contents

| File | Role |
|---|---|
| `conformance.json` | the pack: harness binding (`lwar-runtime.v2-adp`), bootstrap, probe list, authoring rules, instantiation rules, soak extension |
| `*.task.json` | one task template per probe |

## Probes

| `probe_id` | What it separates |
|---|---|
| `content_exactness` | writes a byte-exact marker file with no extra bytes |
| `honest_terminal` | fails honestly on missing input instead of fabricating output |
| `loop_survival_task` | stays resident across ADP slices, waits for a late release, then writes byte-exact output |
| `cancel_while_running` | honors a mid-run cancel and leaves no output behind |
| `graded_impl` | graded implementation quality rather than a pass/fail marker |

Each probe declares its own `timeout_s` and machine-checkable `pass_criteria`
(result status plus artifact SHA-256 where applicable), so scoring never depends
on reading a summary.

## For the OA

Publishing a probe is an ordinary `send`: instantiate the template, then collect
and validate as usual. Only an accepted result feeds calibration or routing
evidence. Note `cancel_while_running` interacts with the notify style — under
exit-notify a cancel cannot reach a task that is already executing (see
[../references/adp-loop.md](../references/adp-loop.md)), so score it against
that contract rather than assuming mid-execution delivery.
