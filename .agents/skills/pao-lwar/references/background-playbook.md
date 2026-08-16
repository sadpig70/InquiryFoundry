# Background ADP playbook

After `/pao-lwar`, the operator is out of the OA↔LWAR path. Official ADP
does **not** depend on host stdout-inject. Detect **live-notify** vs
**exit-notify** once via [host-notify-probe.md](host-notify-probe.md).
The 50-minute timeout check is done when the host **accepts** a
background-Python timeout of >= 50 minutes — do not sleep 50 minutes.

**Official (every host):** `--resident --max-runtime-s 3000` / `lwar.py adp`.
The process **exits** on the first task/control or after 50 idle minutes.
This session reads stdout, handles the event, restarts after `complete`.
Keep the tool parent alive. An orphan watcher prints JSON into nowhere.

```bash
python -u "<PAO_SKILL>/scripts/lwar.py" response REQUEST_ID --resident --max-runtime-s 3000
python -u "<PAO_SKILL>/scripts/lwar.py" adp --identity-file IDENTITY
```

| stdout event | Agent |
|---|---|
| `identity_adopted` | keep `identity_file`; continue until a later line or idle |
| `task_received` | `begin` → work → `complete --result-file`. Then restart `adp` |
| `control` exit 20 | `shutdown`/`retire` stop. else handle and restart |
| `idle_timeout` exit 10 | 50m idle: restart the same command |
| `registration_pending` exit 2 | still waiting for OA: restart the same `response` |

`--background` / `adp_live_notify.py` is only for a probe result of
**live-notify** + `bg_timeout_50m=pass`. Do not use it as the default.
`--detach` / `adp-wait` are not official.

Do not poll mailbox or event files in a tool loop.
`control:ping` is silent on `--background` stdout.
