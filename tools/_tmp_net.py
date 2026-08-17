import subprocess, re

r = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, errors="ignore")
lines = r.stdout.splitlines()
pids = {"21092", "23732"}
print("--- connections for deepseek PIDs ---")
for ln in lines:
    if any(pid in ln.split()[-1:] for pid in pids):
        print(ln)
print("\n--- LISTENING ports (local) ---")
for ln in lines:
    parts = ln.split()
    if len(parts) >= 4 and parts[0] == "TCP" and parts[3] == "LISTENING":
        port = parts[1].rsplit(":", 1)[-1]
        try:
            p = int(parts[-1])
        except ValueError:
            continue
        if p in (21092, 23732) or 3000 <= p <= 30000:
            print(ln)
