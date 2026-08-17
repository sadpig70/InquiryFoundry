import os, re, json

base = os.path.expanduser(r"~\.deepseek")
key_re = re.compile(r"sk-[A-Za-z0-9]{16,}")
token_re = re.compile(r"(bearer|token|api[_-]?key)\s*[=:]\s*[\"']?([A-Za-z0-9\-_.]{16,})", re.I)
url_re = re.compile(r"https?://[^\s\"']+")

found = []
for root, dirs, files in os.walk(base):
    for f in files:
        if f.endswith((".exe", ".version", ".log")):
            continue
        p = os.path.join(root, f)
        try:
            data = open(p, "r", encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        keys = set(key_re.findall(data))
        for k in keys:
            found.append((p, "key", k))
        for m in token_re.finditer(data):
            found.append((p, "cred", m.group(2)[:40]))
        urls = set(u for u in url_re.findall(data) if "deepseek" in u or "api" in u.lower())
        for u in urls:
            found.append((p, "url", u[:120]))

seen = set()
for p, kind, val in found:
    if (p, kind, val) in seen:
        continue
    seen.add((p, kind, val))
    print(f"{kind:5s} {p}")
    print(f"      {val}")
