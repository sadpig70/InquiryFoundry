//! Hand-rolled HTTP/1.1, thread-per-connection (decision S5).
//!
//! The surface is three routes; a framework buys nothing but a dependency
//! whose API this code would then be hostage to. Thread-per-connection is
//! exactly right for a server whose whole job is parking a handful of
//! long-poll calls: four LWARs is four threads.
//!
//! Chunked request bodies are decoded because MCP clients are free to use
//! them; responses always carry Content-Length and Connection: close, which
//! every client understands and which makes connection state a non-problem.

use crate::mcp;
use std::io::{BufRead, BufReader, Read, Write};
use std::net::{TcpListener, TcpStream};
use std::sync::Arc;
use std::time::Duration;

const MAX_BODY: usize = 1 << 20; // 1 MiB — a JSON-RPC frame is tiny
const REQUEST_READ_TIMEOUT_S: u64 = 30;

pub fn serve(ctx: Arc<mcp::Ctx>, port: u16) -> std::io::Result<()> {
    // Invariant 3: loopback only, not configurable.
    let listener = TcpListener::bind(("127.0.0.1", port))?;
    eprintln!("[pao-server] listening on http://127.0.0.1:{port}/mcp");
    for stream in listener.incoming() {
        let Ok(stream) = stream else { continue };
        let ctx = ctx.clone();
        std::thread::spawn(move || {
            let _ = handle_conn(&ctx, stream);
        });
    }
    Ok(())
}

struct Request {
    method: String,
    path: String,
    body: Vec<u8>,
}

fn handle_conn(ctx: &mcp::Ctx, stream: TcpStream) -> std::io::Result<()> {
    stream.set_read_timeout(Some(Duration::from_secs(REQUEST_READ_TIMEOUT_S)))?;
    let mut reader = BufReader::new(stream.try_clone()?);
    let req = match read_request(&mut reader) {
        Ok(Some(r)) => r,
        Ok(None) => return Ok(()), // client closed without a request
        Err(_) => return respond(stream, 400, "text/plain", b"bad request"),
    };

    match (req.method.as_str(), req.path.as_str()) {
        ("POST", "/mcp") => {
            let reply = match serde_json::from_slice::<serde_json::Value>(&req.body) {
                Ok(v) if v.is_array() => mcp::Reply {
                    status: 400,
                    body: Some(serde_json::json!({"jsonrpc": "2.0", "id": null,
                        "error": {"code": -32600, "message": "batching is not supported"}})),
                },
                Ok(v) => mcp::handle(ctx, &v),
                Err(_) => mcp::parse_error(),
            };
            match reply.body {
                Some(b) => respond(stream, reply.status, "application/json", b.to_string().as_bytes()),
                None => respond(stream, reply.status, "text/plain", b""),
            }
        }
        ("GET", "/health") => {
            let body = serde_json::json!({
                "ok": true,
                "server": "pao-server",
                "version": env!("CARGO_PKG_VERSION"),
                "watching": ctx.hub.waiting_ids(),
            });
            respond(stream, 200, "application/json", body.to_string().as_bytes())
        }
        // Stateless (S4): no stream to open, no session to delete.
        ("GET", "/mcp") => respond(stream, 405, "text/plain", b"stateless server; POST only"),
        ("DELETE", "/mcp") => respond(stream, 200, "text/plain", b""),
        _ => respond(stream, 404, "text/plain", b"not found"),
    }
}

fn read_request(reader: &mut BufReader<TcpStream>) -> std::io::Result<Option<Request>> {
    let mut line = String::new();
    if reader.read_line(&mut line)? == 0 {
        return Ok(None);
    }
    let mut parts = line.split_whitespace();
    let method = parts.next().unwrap_or("").to_string();
    let path = parts
        .next()
        .unwrap_or("")
        .split('?')
        .next()
        .unwrap_or("")
        .to_string();

    let mut content_length: Option<usize> = None;
    let mut chunked = false;
    loop {
        let mut h = String::new();
        if reader.read_line(&mut h)? == 0 {
            break;
        }
        let h = h.trim_end();
        if h.is_empty() {
            break;
        }
        let Some((name, value)) = h.split_once(':') else { continue };
        let name = name.trim().to_ascii_lowercase();
        let value = value.trim();
        if name == "content-length" {
            content_length = value.parse::<usize>().ok();
        } else if name == "transfer-encoding" && value.to_ascii_lowercase().contains("chunked") {
            chunked = true;
        }
    }

    let body = if chunked {
        read_chunked(reader)?
    } else if let Some(n) = content_length {
        if n > MAX_BODY {
            return Err(std::io::Error::new(std::io::ErrorKind::InvalidData, "body too large"));
        }
        let mut buf = vec![0u8; n];
        reader.read_exact(&mut buf)?;
        buf
    } else {
        Vec::new()
    };
    Ok(Some(Request { method, path, body }))
}

fn read_chunked(reader: &mut BufReader<TcpStream>) -> std::io::Result<Vec<u8>> {
    let mut body = Vec::new();
    loop {
        let mut size_line = String::new();
        reader.read_line(&mut size_line)?;
        let size = usize::from_str_radix(size_line.trim().split(';').next().unwrap_or("0"), 16)
            .map_err(|_| std::io::Error::new(std::io::ErrorKind::InvalidData, "bad chunk size"))?;
        if body.len() + size > MAX_BODY {
            return Err(std::io::Error::new(std::io::ErrorKind::InvalidData, "body too large"));
        }
        if size == 0 {
            // trailer section until blank line
            loop {
                let mut t = String::new();
                if reader.read_line(&mut t)? == 0 || t.trim_end().is_empty() {
                    break;
                }
            }
            return Ok(body);
        }
        let mut chunk = vec![0u8; size];
        reader.read_exact(&mut chunk)?;
        body.extend_from_slice(&chunk);
        let mut crlf = [0u8; 2];
        reader.read_exact(&mut crlf)?;
    }
}

fn respond(mut stream: TcpStream, status: u16, ctype: &str, body: &[u8]) -> std::io::Result<()> {
    let reason = match status {
        200 => "OK",
        202 => "Accepted",
        400 => "Bad Request",
        404 => "Not Found",
        405 => "Method Not Allowed",
        _ => "",
    };
    let head = format!(
        "HTTP/1.1 {status} {reason}\r\nContent-Type: {ctype}\r\nContent-Length: {}\r\nConnection: close\r\n\r\n",
        body.len()
    );
    stream.write_all(head.as_bytes())?;
    stream.write_all(body)?;
    stream.flush()
}
