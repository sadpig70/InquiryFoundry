import os, json, re, glob, time

base = os.path.expanduser(r"~\.deepseek\sessions")

# list session files by mtime
files = []
for p in glob.glob(os.path.join(base, "*.json")):
    files.append((os.path.getmtime(p), p))
files.sort(reverse=True)
print("Most recent session files:")
for mt, p in files[:5]:
    print("  ", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mt)), os.path.basename(p))

# check checkpoints/latest.json mtime
cp = os.path.join(base, "checkpoints", "latest.json")
print("checkpoint mtime:", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(cp))) if os.path.exists(cp) else "N/A")

# Read the most recent session file: look for top-level metadata and any error strings
mt, newest = files[0]
print("\n=== NEWEST:", newest, "===")
data = open(newest, "r", encoding="utf-8", errors="ignore").read()
print("size:", len(data))
# try to parse as json and print top-level keys
try:
    j = json.loads(data)
    if isinstance(j, dict):
        print("top-level keys:", list(j.keys())[:30])
        for k in ("model", "provider", "endpoint", "base_url", "session_id", "created_at", "updated_at"):
            if k in j:
                print(k, "=", str(j[k])[:200])
except Exception as e:
    print("json parse:", e)

# find error-ish strings
for pat in ["error", "401", "governor", "Authentication", "balance", "insufficient"]:
    idxs = [m.start() for m in re.finditer(pat, data, re.I)]
    if idxs:
        print(f"\npattern '{pat}': {len(idxs)} hits, first at {idxs[0]}")
        for i in idxs[:3]:
            print("   ...", data[max(0,i-80):i+120].replace("\n", " ")[:220])
