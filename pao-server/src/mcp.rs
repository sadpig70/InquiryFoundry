//! Minimal MCP over Streamable HTTP, stateless (decision S4).
//!
//! One JSON-RPC message per POST, answered with application/json. No
//! sessions, no server-initiated stream — the wait semantics live in a
//! blocking tools/call instead (S3), because a long-poll tool call is the
//! one shape every vendor's MCP client is known to handle.

use crate::bus::Bus;
use crate::poll::{Counts, Hub};
use serde_json::{json, Value};
use std::sync::Arc;
use std::time::{Duration, Instant};

// 50 minutes, deliberately under the clients' 60-minute tool timeout:
// the server must answer well before the client gives up, or the reply
// races the abort with zero margin. Both ceiling and default, so even an
// explicit timeout_s: 3600 gets clamped back inside the margin.
pub const WAIT_MAX_S: u64 = 3000;
pub const WAIT_DEFAULT_S: u64 = 3000;

pub struct Ctx {
    pub bus: Arc<Bus>,
    pub hub: Arc<Hub>,
    pub started_at: String,
    pub started_mono: Instant,
}

/// Outcome of one JSON-RPC message: an HTTP status and an optional body.
/// Notifications get 202 with no body, per the Streamable HTTP transport.
pub struct Reply {
    pub status: u16,
    pub body: Option<Value>,
}

fn ok(id: Value, result: Value) -> Reply {
    Reply {
        status: 200,
        body: Some(json!({"jsonrpc": "2.0", "id": id, "result": result})),
    }
}

fn err(id: Value, code: i64, msg: &str) -> Reply {
    Reply {
        status: 200,
        body: Some(json!({"jsonrpc": "2.0", "id": id, "error": {"code": code, "message": msg}})),
    }
}

pub fn parse_error() -> Reply {
    Reply {
        status: 400,
        body: Some(json!({"jsonrpc": "2.0", "id": null,
                          "error": {"code": -32700, "message": "parse error"}})),
    }
}

pub fn handle(ctx: &Ctx, msg: &Value) -> Reply {
    let Some(method) = msg.get("method").and_then(Value::as_str) else {
        // A response or malformed frame; nothing for a stateless server to do.
        return Reply { status: 202, body: None };
    };
    let id = msg.get("id").cloned();
    let params = msg.get("params").cloned().unwrap_or(Value::Null);

    // Requests without an id are notifications: acknowledge and drop.
    let Some(id) = id else {
        return Reply { status: 202, body: None };
    };

    match method {
        "initialize" => {
            // Echo the client's protocol version — the server has no
            // version-dependent behaviour to negotiate.
            let ver = params
                .get("protocolVersion")
                .and_then(Value::as_str)
                .unwrap_or("2025-03-26");
            ok(
                id,
                json!({
                    "protocolVersion": ver,
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "pao-server", "version": env!("CARGO_PKG_VERSION")},
                    "instructions": "PAO file-bus doorbell. Call watcher_wait(lwar_id) to block until mail arrives, then claim and process it with the existing lwar.py path. This server never touches mailbox files."
                }),
            )
        }
        "ping" => ok(id, json!({})),
        "tools/list" => ok(id, json!({"tools": tool_schemas()})),
        "tools/call" => {
            let name = params.get("name").and_then(Value::as_str).unwrap_or("");
            let args = params.get("arguments").cloned().unwrap_or(json!({}));
            match name {
                "watcher_wait" => watcher_wait(ctx, id, &args),
                "watcher_status" => watcher_status(ctx, id),
                _ => err(id, -32602, "unknown tool"),
            }
        }
        _ => err(id, -32601, "method not found"),
    }
}

fn tool_schemas() -> Value {
    json!([
        {
            "name": "watcher_wait",
            "description": "Block until a task or control message arrives in this LWAR's PAO mailbox, or until timeout. Returns counts only — the message itself stays on the bus; claim and process it with lwar.py. Re-call after handling to keep watching.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "lwar_id": {"type": "string", "description": "e.g. LWAR1"},
                    "timeout_s": {"type": "integer", "minimum": 1, "maximum": WAIT_MAX_S,
                                   "description": "server-side wait ceiling; default and maximum 3000 (50min), held 10 minutes under the clients: 60-minute tool timeout so the reply never races the abort"}
                },
                "required": ["lwar_id"]
            }
        },
        {
            "name": "watcher_status",
            "description": "Server liveness and who is currently parked waiting.",
            "inputSchema": {"type": "object", "properties": {}}
        }
    ])
}

fn tool_text(id: Value, payload: Value) -> Reply {
    ok(
        id,
        json!({
            "content": [{"type": "text", "text": payload.to_string()}],
            "structuredContent": payload,
            "isError": false
        }),
    )
}

fn watcher_wait(ctx: &Ctx, id: Value, args: &Value) -> Reply {
    let Some(lwar_id) = args.get("lwar_id").and_then(Value::as_str) else {
        return err(id, -32602, "lwar_id is required");
    };
    if lwar_id.is_empty() || lwar_id.len() > 64 || lwar_id.contains(['/', '.', '\u{5c}']) {
        return err(id, -32602, "lwar_id must be a bare identifier");
    }
    let timeout_s = args
        .get("timeout_s")
        .and_then(Value::as_u64)
        .unwrap_or(WAIT_DEFAULT_S)
        .clamp(1, WAIT_MAX_S);

    let t0 = Instant::now();
    // Register before the immediate check, so mail landing between the check
    // and the park cannot be missed.
    let cell = ctx.hub.register(lwar_id);
    let (tasks, controls) = ctx.bus.counts(lwar_id);
    let first = Counts { tasks, controls };
    let outcome = if first.any() {
        Some(first)
    } else {
        ctx.bus.touch_heartbeat(lwar_id, "watching");
        cell.wait(Duration::from_secs(timeout_s))
    };
    ctx.hub.deregister(lwar_id, &cell);

    let waited_ms = t0.elapsed().as_millis() as u64;
    match outcome {
        Some(c) => tool_text(
            id,
            json!({"arrived": true, "lwar_id": lwar_id,
                   "tasks": c.tasks, "controls": c.controls, "waited_ms": waited_ms}),
        ),
        None => tool_text(
            id,
            json!({"arrived": false, "lwar_id": lwar_id,
                   "tasks": 0, "controls": 0, "waited_ms": waited_ms}),
        ),
    }
}

fn watcher_status(ctx: &Ctx, id: Value) -> Reply {
    tool_text(
        id,
        json!({
            "server": "pao-server",
            "version": env!("CARGO_PKG_VERSION"),
            "started_at": ctx.started_at,
            "uptime_s": ctx.started_mono.elapsed().as_secs(),
            "bus_root": ctx.bus.root().display().to_string(),
            "watching": ctx.hub.waiting_ids(),
            "watchable": ctx.bus.watchable_lwars(),
        }),
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use std::path::PathBuf;

    fn ctx() -> (Ctx, PathBuf) {
        let root = std::env::temp_dir().join(format!("pao-srv-mcp-{}", std::process::id()));
        let _ = fs::remove_dir_all(&root);
        fs::create_dir_all(root.join("mailbox/LWAR1/incoming")).unwrap();
        fs::create_dir_all(root.join("mailbox/LWAR1/control")).unwrap();
        let c = Ctx {
            bus: Arc::new(Bus::new(root.clone())),
            hub: Arc::new(Hub::new()),
            started_at: crate::clock::now_iso(),
            started_mono: Instant::now(),
        };
        (c, root)
    }

    fn call(ctx: &Ctx, body: Value) -> Value {
        handle(ctx, &body).body.unwrap()
    }

    #[test]
    fn initialize_echoes_protocol_version() {
        let (c, root) = ctx();
        let r = call(
            &c,
            json!({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                   "params": {"protocolVersion": "2025-06-18"}}),
        );
        assert_eq!(r["result"]["protocolVersion"], "2025-06-18");
        assert_eq!(r["result"]["serverInfo"]["name"], "pao-server");
        let _ = fs::remove_dir_all(root);
    }

    #[test]
    fn notification_is_202_without_body() {
        let (c, root) = ctx();
        let r = handle(
            &c,
            &json!({"jsonrpc": "2.0", "method": "notifications/initialized"}),
        );
        assert_eq!(r.status, 202);
        assert!(r.body.is_none());
        let _ = fs::remove_dir_all(root);
    }

    #[test]
    fn unknown_method_is_32601() {
        let (c, root) = ctx();
        let r = call(&c, json!({"jsonrpc": "2.0", "id": 5, "method": "resources/list"}));
        assert_eq!(r["error"]["code"], -32601);
        let _ = fs::remove_dir_all(root);
    }

    #[test]
    fn wait_returns_immediately_when_mail_already_there() {
        let (c, root) = ctx();
        fs::write(root.join("mailbox/LWAR1/incoming/001_t.json"), "{}").unwrap();
        let r = call(
            &c,
            json!({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                   "params": {"name": "watcher_wait",
                              "arguments": {"lwar_id": "LWAR1", "timeout_s": 30}}}),
        );
        let sc = &r["result"]["structuredContent"];
        assert_eq!(sc["arrived"], true);
        assert_eq!(sc["tasks"], 1);
        assert!(sc["waited_ms"].as_u64().unwrap() < 2000);
        let _ = fs::remove_dir_all(root);
    }

    #[test]
    fn wait_times_out_clean() {
        let (c, root) = ctx();
        let r = call(
            &c,
            json!({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                   "params": {"name": "watcher_wait",
                              "arguments": {"lwar_id": "LWAR1", "timeout_s": 1}}}),
        );
        assert_eq!(r["result"]["structuredContent"]["arrived"], false);
        assert!(c.hub.waiting_ids().is_empty(), "waiter must deregister");
        let _ = fs::remove_dir_all(root);
    }

    #[test]
    fn schema_advertises_the_hour_ceiling() {
        // 50 minutes of wait against a 60-minute client tool timeout: one turn
        // per idle hour, with ten minutes of margin so the reply never races the abort.
        const CLIENT_TOOL_TIMEOUT_S: u64 = 3600; // operator-configured, per runtime
        assert_eq!(WAIT_MAX_S, 3000);
        assert_eq!(WAIT_DEFAULT_S, WAIT_MAX_S);
        // The whole point: the server always answers before the client aborts.
        assert!(WAIT_MAX_S + 300 <= CLIENT_TOOL_TIMEOUT_S);
        let schema = tool_schemas();
        assert_eq!(schema[0]["inputSchema"]["properties"]["timeout_s"]["maximum"], 3000);
    }

    #[test]
    fn lwar_id_path_tricks_rejected() {
        let (c, root) = ctx();
        for bad in ["../LWAR1", "a/b", ""] {
            let r = call(
                &c,
                json!({"jsonrpc": "2.0", "id": 4, "method": "tools/call",
                       "params": {"name": "watcher_wait", "arguments": {"lwar_id": bad}}}),
            );
            assert_eq!(r["error"]["code"], -32602, "should reject {bad:?}");
        }
        let _ = fs::remove_dir_all(root);
    }
}
