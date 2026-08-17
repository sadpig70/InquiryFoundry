import os, json

cp = os.path.join(os.path.expanduser(r"~\.deepseek\sessions"), "checkpoints", "latest.json")
data = open(cp, "r", encoding="utf-8", errors="ignore").read()
j = json.loads(data)
print("top-level keys:", list(j.keys()))
meta = j.get("metadata", {})
print("\nmetadata:", json.dumps(meta, ensure_ascii=False, indent=1)[:3000])

msgs = j.get("messages", [])
print("\nmessages:", len(msgs))
# show roles
from collections import Counter
print(Counter(m.get("role") for m in msgs))

# find model/usage fields in any message
import re
model_hits = set()
for m in msgs:
    if isinstance(m, dict):
        for k in m:
            if k.lower() in ("model", "provider"):
                model_hits.add((k, str(m[k])[:100]))
        if "usage" in m:
            print("usage on msg:", json.dumps(m["usage"], ensure_ascii=False)[:500])
        c = m.get("content")
        if isinstance(c, str) and ("model" in c.lower() or "usage" in c.lower()):
            pass
print("\nmodel/provider fields:", model_hits)

# raw scan for '"model"' and '"usage"' occurrences near top
for pat in ['"model"', '"usage"', '"cost"', '"endpoint"', '"provider"', '"base_url"', '"request_id"']:
    idxs = [i for i in range(len(data)) if data.startswith(pat, i)]
    print(pat, "hits:", len(idxs), "first:", idxs[0] if idxs else None)
