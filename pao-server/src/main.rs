//! pao-server — central watcher for PAO LWARs, exposed as a stateless MCP
//! Streamable HTTP endpoint on loopback.
//!
//! What it replaces: one fragile resident watcher per vendor runtime, whose
//! silent deaths and frozen heartbeats produced most of this project's
//! operational incidents. What it does not replace: anything that touches the
//! bus. Claiming, leases, submission — the existing lwar.py path, unchanged.
//!
//!   pao-server [--root <dir>] [--port <n>] [--poll-secs <n>]
//!
//!   --root       the .pao directory (default ./.pao)
//!   --port       loopback port (default 8811)
//!   --poll-secs  bus poll interval (default 5)

mod bus;
mod clock;
mod http;
mod mcp;
mod poll;

use std::path::PathBuf;
use std::sync::Arc;
use std::time::Instant;

fn arg_value(args: &[String], name: &str) -> Option<String> {
    args.iter()
        .position(|a| a == name)
        .and_then(|i| args.get(i + 1))
        .cloned()
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.iter().any(|a| a == "--help" || a == "-h") {
        eprintln!("usage: pao-server [--root <dir>] [--port <n>] [--poll-secs <n>]");
        return;
    }
    let root = PathBuf::from(arg_value(&args, "--root").unwrap_or_else(|| "./.pao".into()));
    let port: u16 = arg_value(&args, "--port")
        .and_then(|v| v.parse().ok())
        .unwrap_or(8811);
    let poll_secs: u64 = arg_value(&args, "--poll-secs")
        .and_then(|v| v.parse().ok())
        .unwrap_or(5);

    if !root.join("mailbox").is_dir() {
        eprintln!(
            "[pao-server] {} has no mailbox/ — is --root pointing at a .pao directory?",
            root.display()
        );
        std::process::exit(2);
    }

    let started_at = clock::now_iso();
    let bus = Arc::new(bus::Bus::new(root));
    let hub = Arc::new(poll::Hub::new());
    let ctx = Arc::new(mcp::Ctx {
        bus: bus.clone(),
        hub: hub.clone(),
        started_at: started_at.clone(),
        started_mono: Instant::now(),
    });

    eprintln!(
        "[pao-server] v{} root={} poll={}s",
        env!("CARGO_PKG_VERSION"),
        bus.root().display(),
        poll_secs
    );
    poll::spawn_poller(bus, hub, port, poll_secs, started_at);
    if let Err(e) = http::serve(ctx, port) {
        eprintln!("[pao-server] bind failed: {e}");
        std::process::exit(1);
    }
}
