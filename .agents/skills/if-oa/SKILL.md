---
name: if-oa
description: IF overlay on pao-oa. send/collect/recover/status/presence/audit-health/validate/workflow-status/control.
---

# if-oa

```bash
python .agents/skills/if-oa/scripts/if_oa.py status
python .agents/skills/if-oa/scripts/if_oa.py send --lwar-id LWAR1 --task-file task.json
python .agents/skills/if-oa/scripts/if_oa.py validate --task-id TASK
python .agents/skills/if-oa/scripts/if_oa.py control --lwar-id LWAR1 --command shutdown
```

No `doctor`. No `pao_runtime` in this folder. No graph writes. Cycle owns `if_cycle.py`.
