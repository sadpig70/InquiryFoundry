"""Sleep 11 minutes then exit. Background-wait test."""
import time
import datetime

print(f"[sleep11] start: {datetime.datetime.now().isoformat(timespec='seconds')}", flush=True)
time.sleep(11 * 60)
print(f"[sleep11] done : {datetime.datetime.now().isoformat(timespec='seconds')}", flush=True)
