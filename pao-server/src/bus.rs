//! Read-only view of the PAO file bus, plus the server's two permitted writes.
//!
//! Decision S1: this server is a doorbell, not a mailman. It never moves,
//! deletes, or creates mailbox files — claiming, leases and submission stay in
//! the existing lwar.py paths, so a server death strands nothing (the 7.6
//! failure this design exists to avoid recentralising).
//!
//! The two writes (S2): a waiting LWAR's heartbeat.json, preserving every
//! identity field and touching only last_seen/status; and the server's own
//! liveness file under var/. A missing heartbeat file is never created — an
//! LWAR that has not registered has no heartbeat for us to keep warm.

use serde_json::Value;
use std::fs;
use std::path::{Path, PathBuf};

pub struct Bus {
    root: PathBuf, // the .pao directory
}

impl Bus {
    pub fn new(root: PathBuf) -> Self {
        Bus { root }
    }

    pub fn root(&self) -> &Path {
        &self.root
    }

    /// LWARs worth polling: registry slots in state on/draining.
    /// Decision S7: a registry that fails to parse degrades to every mailbox
    /// directory rather than to nothing — schema drift must not silence the
    /// doorbell.
    pub fn watchable_lwars(&self) -> Vec<String> {
        match self.registry_watchable() {
            Some(ids) if !ids.is_empty() => ids,
            _ => self.all_mailbox_dirs(),
        }
    }

    fn registry_watchable(&self) -> Option<Vec<String>> {
        let raw = fs::read_to_string(self.root.join("var/registry/lwar_registry.json")).ok()?;
        let doc: Value = serde_json::from_str(&raw).ok()?;
        let slots = doc.get("slots")?.as_object()?;
        let mut out = Vec::new();
        for (id, slot) in slots {
            let state = slot.get("state").and_then(Value::as_str).unwrap_or("");
            if state == "on" || state == "draining" {
                out.push(id.clone());
            }
        }
        out.sort();
        Some(out)
    }

    fn all_mailbox_dirs(&self) -> Vec<String> {
        let mut out = Vec::new();
        if let Ok(entries) = fs::read_dir(self.root.join("mailbox")) {
            for e in entries.flatten() {
                if e.path().is_dir() {
                    if let Some(name) = e.file_name().to_str() {
                        out.push(name.to_string());
                    }
                }
            }
        }
        out.sort();
        out
    }

    fn count_json(&self, dir: &Path) -> usize {
        let Ok(entries) = fs::read_dir(dir) else {
            return 0;
        };
        entries
            .flatten()
            .filter(|e| {
                e.path().extension().and_then(|x| x.to_str()) == Some("json")
                    && e.path().is_file()
            })
            .count()
    }

    /// (pending tasks, pending controls) for one LWAR.
    pub fn counts(&self, lwar_id: &str) -> (usize, usize) {
        let mb = self.root.join("mailbox").join(lwar_id);
        (
            self.count_json(&mb.join("incoming")),
            self.count_json(&mb.join("control")),
        )
    }

    /// S2(a): refresh a waiting LWAR's heartbeat. Read-modify-write that
    /// preserves identity (instance_id, generation, lwar_id, schema_version,
    /// current_task_id) — only last_seen and status change. No file, no write.
    pub fn touch_heartbeat(&self, lwar_id: &str, status: &str) -> bool {
        let path = self.root.join("mailbox").join(lwar_id).join("heartbeat.json");
        let Ok(raw) = fs::read_to_string(&path) else {
            return false;
        };
        let Ok(mut doc) = serde_json::from_str::<Value>(&raw) else {
            return false;
        };
        let Some(obj) = doc.as_object_mut() else {
            return false;
        };
        obj.insert("last_seen".into(), Value::String(crate::clock::now_iso()));
        obj.insert("status".into(), Value::String(status.to_string()));
        self.atomic_write(&path, &doc)
    }

    /// S2(b): the server's own liveness file, so oa.py status (or a person)
    /// can tell a dead notification layer from a quiet one.
    pub fn touch_server(&self, port: u16, watching: &[String], started_at: &str) -> bool {
        let path = self.root.join("var").join("pao_server.json");
        let doc = serde_json::json!({
            "schema_version": "pao.server.v1",
            "last_seen": crate::clock::now_iso(),
            "started_at": started_at,
            "port": port,
            "bind": "127.0.0.1",
            "watching": watching,
        });
        self.atomic_write(&path, &doc)
    }

    /// Same tmp-then-rename discipline as the rest of the bus; the tmp name
    /// matches the .pao-*.tmp convention so existing crash-debris cleanup
    /// already covers ours. On Windows a rename over an open file can fail —
    /// we report failure and let the next poll retry rather than removing the
    /// destination under a reader.
    fn atomic_write(&self, path: &Path, doc: &Value) -> bool {
        let Some(dir) = path.parent() else {
            return false;
        };
        let tmp = dir.join(format!(".pao-server-{}.tmp", std::process::id()));
        let body = match serde_json::to_string_pretty(doc) {
            Ok(b) => b,
            Err(_) => return false,
        };
        if fs::write(&tmp, body).is_err() {
            return false;
        }
        if fs::rename(&tmp, path).is_err() {
            let _ = fs::remove_file(&tmp);
            return false;
        }
        true
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn scratch(tag: &str) -> PathBuf {
        let d = std::env::temp_dir().join(format!("pao-srv-test-{}-{}", tag, std::process::id()));
        let _ = fs::remove_dir_all(&d);
        fs::create_dir_all(d.join("mailbox/LWARX/incoming")).unwrap();
        fs::create_dir_all(d.join("mailbox/LWARX/control")).unwrap();
        fs::create_dir_all(d.join("var/registry")).unwrap();
        d
    }

    #[test]
    fn registry_failure_degrades_to_directory_scan() {
        let root = scratch("reg-fail");
        fs::write(root.join("var/registry/lwar_registry.json"), "{not json").unwrap();
        let bus = Bus::new(root.clone());
        assert_eq!(bus.watchable_lwars(), vec!["LWARX".to_string()]);
        let _ = fs::remove_dir_all(root);
    }

    #[test]
    fn registry_filters_by_state() {
        let root = scratch("reg-state");
        let reg = serde_json::json!({"slots": {
            "LWARA": {"state": "on"},
            "LWARB": {"state": "off"},
            "LWARC": {"state": "draining"},
        }});
        fs::write(root.join("var/registry/lwar_registry.json"), reg.to_string()).unwrap();
        let bus = Bus::new(root.clone());
        assert_eq!(
            bus.watchable_lwars(),
            vec!["LWARA".to_string(), "LWARC".to_string()]
        );
        let _ = fs::remove_dir_all(root);
    }

    #[test]
    fn counts_only_json_files() {
        let root = scratch("counts");
        fs::write(root.join("mailbox/LWARX/incoming/001_task.json"), "{}").unwrap();
        fs::write(root.join("mailbox/LWARX/incoming/.pao-x.tmp"), "{}").unwrap();
        fs::write(root.join("mailbox/LWARX/control/control-a.json"), "{}").unwrap();
        let bus = Bus::new(root.clone());
        assert_eq!(bus.counts("LWARX"), (1, 1));
        let _ = fs::remove_dir_all(root);
    }

    #[test]
    fn heartbeat_preserves_identity_and_missing_file_stays_missing() {
        let root = scratch("hb");
        let bus = Bus::new(root.clone());
        // No file: no write, nothing created.
        assert!(!bus.touch_heartbeat("LWARX", "watching"));
        assert!(!root.join("mailbox/LWARX/heartbeat.json").exists());
        // Existing file: identity survives, last_seen/status move.
        let hb = serde_json::json!({
            "schema_version": "pao.heartbeat.v1",
            "lwar_id": "LWARX",
            "instance_id": "lwar-instance-abc",
            "generation": 7,
            "current_task_id": null,
            "status": "control",
            "last_seen": "2020-01-01T00:00:00.000000Z",
        });
        let path = root.join("mailbox/LWARX/heartbeat.json");
        fs::write(&path, hb.to_string()).unwrap();
        assert!(bus.touch_heartbeat("LWARX", "watching"));
        let out: Value = serde_json::from_str(&fs::read_to_string(&path).unwrap()).unwrap();
        assert_eq!(out["instance_id"], "lwar-instance-abc");
        assert_eq!(out["generation"], 7);
        assert_eq!(out["status"], "watching");
        assert!(out["last_seen"].as_str().unwrap() > "2020-01-01");
        let _ = fs::remove_dir_all(root);
    }
}
