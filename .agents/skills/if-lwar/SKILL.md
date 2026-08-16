---
name: if-lwar
description: IF LWAR dispatch. Visibility jail then role skill. complete --result-file only.
---

# if-lwar

```bash
python .agents/skills/if-lwar/scripts/if_lwar.py --self-test
python .agents/skills/if-lwar/scripts/if_lwar.py --stub --role generate --lwar-id LWAR1 --jail PATH --inbox PATH --outbox PATH
python .agents/skills/if-lwar/scripts/if_lwar.py --validate-only --role generate --lwar-id LWAR1 --jail PATH --inbox PATH --outbox PATH
```

`--stub` is the deterministic dispatcher. Live runs write the outbox via the role SKILL (`AI_`) then `--validate-only`. Stub markers and empty lists fail unless `--stub`.

Forbidden: reading `allocation.yaml`, `graph/`, `memory/`, other jails.
Forbidden: `--artifacts` on complete. Use PAO `--result-file`.
