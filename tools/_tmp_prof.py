import os, subprocess, glob

# 1) Find pwsh profile files
profiles = []
for pat in [
    os.path.expanduser(r"~\Documents\PowerShell\Microsoft.PowerShell_profile.ps1"),
    os.path.expanduser(r"~\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1"),
    os.path.expanduser(r"~\OneDrive\Documents\PowerShell\Microsoft.PowerShell_profile.ps1"),
]:
    if os.path.exists(pat):
        profiles.append(pat)
print("profiles found:", profiles)
for p in profiles:
    txt = open(p, "r", encoding="utf-8", errors="ignore").read()
    print(f"\n=== {p} (len {len(txt)}) ===")
    for i, ln in enumerate(txt.splitlines()):
        if "deepseek" in ln.lower() or "sk-" in ln or "DEEPSEEK" in ln:
            print(f"  [{i}] {ln[:300]}")

# 2) Search full PSReadLine history for key-ish patterns
hist = os.path.expanduser(r"~\AppData\Roaming\Microsoft\Windows\PowerShell\PSReadLine\ConsoleHost_history.txt")
lines = open(hist, "r", encoding="utf-8", errors="ignore").read().splitlines()
print("\n=== history lines with sk-/api-key/login/env ===")
for i, ln in enumerate(lines):
    low = ln.lower()
    if any(s in low for s in ("sk-", "api-key", "api_key", "login", "deepseek_env", "auth set", "DEEPSEEK_")):
        print(f"  [{i}] {ln[:300]}")
