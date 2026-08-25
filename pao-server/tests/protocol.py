"""Live protocol test: a real HTTP client against a running pao-server.

The unit tests prove the pieces; this proves the wire. It builds a scratch
.pao, starts the actual binary, and speaks MCP Streamable HTTP at it the way
a vendor runtime's client would — including the paths that bit us before:
mail landing mid-wait, heartbeat identity preservation, chunked bodies.

    python tests/protocol.py [path-to-binary]
"""
import http.client
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time

PORT = 8899
FAILS = []


def check(name, cond, detail=""):
    tag = "ok " if cond else "FAIL"
    print("  %s %s %s" % (tag, name, detail if not cond else ""))
    if not cond:
        FAILS.append(name)


def rpc(payload, chunked=False):
    conn = http.client.HTTPConnection("127.0.0.1", PORT, timeout=630)
    body = json.dumps(payload).encode()
    if chunked:
        conn.putrequest("POST", "/mcp")
        conn.putheader("Content-Type", "application/json")
        conn.putheader("Transfer-Encoding", "chunked")
        conn.endheaders()
        # two chunks, hex sizes, CRLF framing
        half = len(body) // 2
        for part in (body[:half], body[half:]):
            conn.send(("%x\r\n" % len(part)).encode() + part + b"\r\n")
        conn.send(b"0\r\n\r\n")
    else:
        conn.request("POST", "/mcp", body, {"Content-Type": "application/json"})
    resp = conn.getresponse()
    raw = resp.read()
    conn.close()
    return resp.status, (json.loads(raw) if raw else None)


def get(path):
    conn = http.client.HTTPConnection("127.0.0.1", PORT, timeout=10)
    conn.request("GET", path)
    resp = conn.getresponse()
    raw = resp.read()
    conn.close()
    return resp.status, raw


def main():
    binary = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(__file__), "..", "target", "debug", "pao-server.exe")

    root = tempfile.mkdtemp(prefix="pao-proto-")
    pao = os.path.join(root, ".pao")
    for lid in ("LWAR1", "LWAR2"):
        os.makedirs(os.path.join(pao, "mailbox", lid, "incoming"))
        os.makedirs(os.path.join(pao, "mailbox", lid, "control"))
    os.makedirs(os.path.join(pao, "var", "registry"))
    with open(os.path.join(pao, "var", "registry", "lwar_registry.json"), "w") as f:
        json.dump({"schema_version": "x", "slots": {
            "LWAR1": {"state": "on"}, "LWAR2": {"state": "off"}}}, f)
    hb = {"schema_version": "pao.heartbeat.v1", "lwar_id": "LWAR1",
          "instance_id": "lwar-instance-proto", "generation": 3,
          "current_task_id": None, "status": "control",
          "last_seen": "2020-01-01T00:00:00.000000Z"}
    hb_path = os.path.join(pao, "mailbox", "LWAR1", "heartbeat.json")
    with open(hb_path, "w") as f:
        json.dump(hb, f)

    srv = subprocess.Popen(
        [binary, "--root", pao, "--port", str(PORT), "--poll-secs", "1"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        # wait for bind
        for _ in range(50):
            try:
                get("/health")
                break
            except OSError:
                time.sleep(0.1)

        print("[protocol handshake]")
        st, r = rpc({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                     "params": {"protocolVersion": "2025-06-18",
                                "capabilities": {}, "clientInfo": {"name": "t"}}})
        check("initialize 200", st == 200)
        check("protocolVersion echoed",
              r["result"]["protocolVersion"] == "2025-06-18")
        check("serverInfo name", r["result"]["serverInfo"]["name"] == "pao-server")

        st, r = rpc({"jsonrpc": "2.0", "method": "notifications/initialized"})
        check("notification -> 202 empty", st == 202 and r is None)

        st, r = rpc({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        names = [t["name"] for t in r["result"]["tools"]]
        check("tools/list has both tools",
              names == ["watcher_wait", "watcher_status"], names)

        st, r = rpc([{"jsonrpc": "2.0", "id": 9, "method": "ping"}])
        check("batch rejected -32600", r["error"]["code"] == -32600)

        st, raw = get("/mcp")
        check("GET /mcp -> 405", st == 405)
        st, raw = get("/health")
        check("GET /health ok", st == 200 and json.loads(raw)["ok"] is True)

        print("[chunked transfer]")
        st, r = rpc({"jsonrpc": "2.0", "id": 3, "method": "ping"}, chunked=True)
        check("chunked ping", st == 200 and r["result"] == {})

        print("[watcher_wait: mail already present]")
        with open(os.path.join(pao, "mailbox", "LWAR1", "incoming",
                               "001_task-x.json"), "w") as f:
            f.write("{}")
        t0 = time.time()
        st, r = rpc({"jsonrpc": "2.0", "id": 4, "method": "tools/call",
                     "params": {"name": "watcher_wait",
                                "arguments": {"lwar_id": "LWAR1", "timeout_s": 30}}})
        sc = r["result"]["structuredContent"]
        check("immediate arrival", sc["arrived"] is True and sc["tasks"] == 1)
        check("immediate is fast", time.time() - t0 < 2.0,
              "%.1fs" % (time.time() - t0))
        os.remove(os.path.join(pao, "mailbox", "LWAR1", "incoming", "001_task-x.json"))

        print("[watcher_wait: mail lands mid-wait]")
        def drop_later():
            time.sleep(2.0)
            with open(os.path.join(pao, "mailbox", "LWAR1", "control",
                                   "control-y.json"), "w") as f:
                f.write("{}")
        threading.Thread(target=drop_later, daemon=True).start()
        t0 = time.time()
        st, r = rpc({"jsonrpc": "2.0", "id": 5, "method": "tools/call",
                     "params": {"name": "watcher_wait",
                                "arguments": {"lwar_id": "LWAR1", "timeout_s": 30}}})
        sc = r["result"]["structuredContent"]
        waited = time.time() - t0
        check("mid-wait arrival", sc["arrived"] is True and sc["controls"] == 1)
        check("woken within poll budget", 1.5 < waited < 8.0, "%.1fs" % waited)

        print("[heartbeat identity]")
        with open(hb_path) as f:
            after = json.load(f)
        check("identity preserved",
              after["instance_id"] == "lwar-instance-proto"
              and after["generation"] == 3)
        check("last_seen advanced", after["last_seen"] > "2025-01-01")
        check("status is watching", after["status"] == "watching")
        check("no heartbeat invented for LWAR2",
              not os.path.exists(os.path.join(pao, "mailbox", "LWAR2",
                                              "heartbeat.json")))

        print("[watcher_wait: timeout path]")
        os.remove(os.path.join(pao, "mailbox", "LWAR1", "control", "control-y.json"))
        t0 = time.time()
        st, r = rpc({"jsonrpc": "2.0", "id": 6, "method": "tools/call",
                     "params": {"name": "watcher_wait",
                                "arguments": {"lwar_id": "LWAR1", "timeout_s": 2}}})
        sc = r["result"]["structuredContent"]
        check("clean timeout", sc["arrived"] is False)
        check("timeout honoured", 1.5 < time.time() - t0 < 5.0)

        print("[server liveness + status tool]")
        st, r = rpc({"jsonrpc": "2.0", "id": 7, "method": "tools/call",
                     "params": {"name": "watcher_status", "arguments": {}}})
        sc = r["result"]["structuredContent"]
        check("status watchable respects registry states",
              sc["watchable"] == ["LWAR1"], sc["watchable"])
        live = os.path.join(pao, "var", "pao_server.json")
        check("server liveness file written", os.path.exists(live))
        if os.path.exists(live):
            with open(live) as f:
                lv = json.load(f)
            check("liveness schema", lv["schema_version"] == "pao.server.v1"
                  and lv["bind"] == "127.0.0.1")

        print("[mailbox untouched]")
        # the doorbell must not have moved/created anything in mailbox dirs
        for lid in ("LWAR1", "LWAR2"):
            for sub in ("incoming", "control"):
                left = os.listdir(os.path.join(pao, "mailbox", lid, sub))
                check("%s/%s empty" % (lid, sub), left == [], left)
    finally:
        srv.terminate()
        srv.wait(timeout=10)
        shutil.rmtree(root, ignore_errors=True)

    print()
    if FAILS:
        print("FAILED: %d -> %s" % (len(FAILS), FAILS))
        return 1
    print("protocol test: all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
