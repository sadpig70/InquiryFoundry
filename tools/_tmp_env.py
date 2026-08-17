import os, subprocess

print("=== env vars (proxy/key related) ===")
for k, v in sorted(os.environ.items()):
    kl = k.lower()
    if any(s in kl for s in ("proxy", "key", "token", "api", "secret", "deepseek", "openai")):
        masked = v
        if any(s in kl for s in ("key", "token", "secret")):
            masked = v[:8] + "..." + v[-4:] if len(v) > 14 else "***"
        print(f"{k} = {masked}")

print("\n=== winhttp proxy ===")
r = subprocess.run(["netsh", "winhttp", "show", "proxy"], capture_output=True, text=True)
print(r.stdout.strip() or r.stderr.strip())

print("\n=== IE/registry proxy ===")
r = subprocess.run(
    ["reg", "query", "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings",
     "/v", "ProxyEnable"], capture_output=True, text=True)
print(r.stdout.strip() or r.stderr.strip())
r = subprocess.run(
    ["reg", "query", "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings",
     "/v", "ProxyServer"], capture_output=True, text=True)
print(r.stdout.strip() or r.stderr.strip())
