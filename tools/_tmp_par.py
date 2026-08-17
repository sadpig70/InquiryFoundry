import subprocess, json

# Get parent process chain for PID 23732 and 21092
script = r"""
$ids = @(23732, 21092)
$all = Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name,ExecutablePath,CommandLine
foreach ($id in $ids) {
  $cur = $id
  $depth = 0
  while ($cur -and $depth -lt 6) {
    $p = $all | Where-Object { $_.ProcessId -eq $cur }
    if (-not $p) { break }
    [PSCustomObject]@{
      Depth = $depth
      PID = $p.ProcessId
      PPID = $p.ParentProcessId
      Name = $p.Name
      Cmd = $p.CommandLine
    }
    $cur = $p.ParentProcessId
    $depth++
  }
} | ConvertTo-Json -Depth 3 -Compress
"""
r = subprocess.run(["D:\\Tools\\PS7\\7.6.4\\pwsh.exe", "-NoProfile", "-Command", script],
                   capture_output=True, text=True, timeout=60)
print("OUT:", r.stdout.strip()[:4000])
print("ERR:", r.stderr.strip()[:1000])

# PSReadLine history files
import os, glob
hist_dirs = [
    os.path.expanduser(r"~\AppData\Roaming\Microsoft\Windows\PowerShell\PSReadLine\ConsoleHost_history.txt"),
    os.path.expanduser(r"~\AppData\Roaming\Microsoft\PowerShell\PSReadLine\ConsoleHost_history.txt"),
]
for h in hist_dirs:
    if os.path.exists(h):
        print("\n=== HISTORY:", h, "===")
        lines = open(h, "r", encoding="utf-8", errors="ignore").read().splitlines()
        # show lines mentioning deepseek
        for i, ln in enumerate(lines):
            if "deepseek" in ln.lower() or "DEEPSEEK" in ln:
                print(f"  [{i}] {ln[:300]}")
