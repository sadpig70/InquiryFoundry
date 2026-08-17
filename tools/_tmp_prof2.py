import os, subprocess

hist = os.path.expanduser(r"~\AppData\Roaming\Microsoft\Windows\PowerShell\PSReadLine\ConsoleHost_history.txt")
lines = open(hist, "r", encoding="utf-8", errors="ignore").read().splitlines()

print("=== history context around deepseek_env (11980-12010) ===")
for i in range(11980, min(12010, len(lines))):
    print(f"  [{i}] {lines[i][:300]}")

print("\n=== last 40 history lines ===")
for i in range(max(0, len(lines)-40), len(lines)):
    print(f"  [{i}] {lines[i][:300]}")

# bash history
bh = os.path.expanduser(r"~\.bash_history")
if os.path.exists(bh):
    print("\n=== .bash_history deepseek lines ===")
    bl = open(bh, "r", encoding="utf-8", errors="ignore").read().splitlines()
    for i, ln in enumerate(bl):
        if "deepseek" in ln.lower() or "sk-" in ln or "DEEPSEEK" in ln:
            print(f"  [{i}] {ln[:300]}")

# bashrc/profile
for p in [os.path.expanduser(r"~\.bashrc"), os.path.expanduser(r"~\.bash_profile"), os.path.expanduser(r"~\.profile")]:
    if os.path.exists(p):
        txt = open(p, "r", encoding="utf-8", errors="ignore").read()
        if "deepseek" in txt.lower() or "sk-" in txt or "DEEPSEEK" in txt:
            print(f"\n=== {p} ===")
            for i, ln in enumerate(txt.splitlines()):
                if "deepseek" in ln.lower() or "sk-" in ln or "DEEPSEEK" in ln:
                    print(f"  [{i}] {ln[:300]}")

# fixed parent-process chain query
script = r"""
$all = @(Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name,CommandLine)
$out = @()
foreach ($id in @(23732, 21092)) {
  $cur = $id
  $depth = 0
  while ($cur -and $depth -lt 6) {
    $p = $all | Where-Object { $_.ProcessId -eq $cur }
    if (-not $p) { break }
    $out += [PSCustomObject]@{ Depth=$depth; PID=$p.ProcessId; PPID=$p.ParentProcessId; Name=$p.Name; Cmd=$p.CommandLine }
    $cur = $p.ParentProcessId
    $depth++
  }
}
$out | ConvertTo-Json -Depth 3 -Compress
"""
r = subprocess.run(["D:\\Tools\\PS7\\7.6.4\\pwsh.exe", "-NoProfile", "-Command", script],
                   capture_output=True, text=True, timeout=60)
print("\n=== parent chain ===")
print(r.stdout.strip()[:4000] or r.stderr.strip()[:1000])
