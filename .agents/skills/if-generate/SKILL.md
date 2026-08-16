---
name: if-generate
description: IF EXPLORE generator. mine_min + operators. local_id only. No question_id.
---

# if-generate

Read jail inbox + hints only. Write seed_outbox list.

- Evidence omitted → drop seed (D18).
- Do not write `question_id`.
- Operators only from `allocation_slice.operators`.

```bash
python .agents/skills/if-lwar/scripts/if_lwar.py --role generate ...
```
