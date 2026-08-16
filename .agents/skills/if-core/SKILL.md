---
name: if-core
description: InquiryFoundry contracts and deterministic I/O. Schemas, gates, state, store, bus, cycle.
---

# if-core

Single source of IF contracts. Not a role skill.

```bash
python .agents/skills/if-core/scripts/validate.py --kind qo path.yaml
python .agents/skills/if-core/scripts/if_cycle.py run --brief B --lwars LWAR1:anthropic,LWAR2:openai,LWAR3:moonshot
python .agents/skills/if-core/scripts/if_cycle.py run --pao --brief B --lwars LWAR1:anthropic,LWAR2:openai,LWAR3:moonshot --if-root .if
python .agents/skills/if-core/scripts/if_cycle.py close --run RUN-... --if-root .if
```

PPR authority: `.pgf/DESIGN-InquiryFoundry.md` @v:0.2.3.
Do not copy `pao_runtime`. Do not mint `question_id` from workers.
