import os

print("total env vars:", len(os.environ))
hits = []
for k, v in sorted(os.environ.items()):
    if "sk-" in v.lower() or len(v) > 20 and any(c.isalnum() for c in v):
        if "sk-" in v.lower():
            hits.append((k, v))
print("\nvalues containing 'sk-':")
for k, v in hits:
    print(f"  {k} = {v[:12]}...{v[-4:]}")
if not hits:
    print("  NONE")

# Also check if DEEPSEEK_API_KEY exists with a different name
print("\nall vars containing 'SEEK':", [k for k in os.environ if "seek" in k.lower()])
print("all vars containing 'NIM':", [k for k in os.environ if "nim" in k.lower()])
