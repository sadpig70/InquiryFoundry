import re

p = r"D:\Tools\deepseek-tui\node_modules\deepseek-tui\bin\downloads\deepseek-tui.exe"
data = open(p, "rb").read()
print("size:", len(data))

pats = [rb"Authorization", rb"Bearer", rb"x-api-key", rb"api[_-]key", rb"user/balance",
        rb"chat/completions", rb"beta", rb"User-Agent", rb"base_url", rb"api_base",
        rb"sk-", rb"governor"]

for pat in pats:
    hits = [m.start() for m in re.finditer(pat, data, re.I)]
    print(f"\n--- {pat.decode()} : {len(hits)} hits ---")
    for h in hits[:8]:
        ctx = data[max(0, h - 60): h + 80]
        # printable
        try:
            s = ctx.decode("utf-8", "ignore")
        except Exception:
            s = repr(ctx)
        print("   ", s.replace("\n", " ")[:150])
