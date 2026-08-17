import subprocess, os

# Get process info via PowerShell CIM (run through pwsh path from AGENTS.md)
pids = ["23732", "21092"]
for pid in pids:
    r = subprocess.run(
        ["D:\\Tools\\PS7\\7.6.4\\pwsh.exe", "-NoProfile", "-Command",
         f"Get-CimInstance Win32_Process -Filter 'ProcessId={pid}' | Select-Object ProcessId,CreationDate,ExecutablePath,CommandLine | ConvertTo-Json -Compress"],
        capture_output=True, text=True, timeout=30)
    print("PID", pid, "rc=", r.returncode)
    print("OUT:", r.stdout.strip()[:2000])
    print("ERR:", r.stderr.strip()[:500])
