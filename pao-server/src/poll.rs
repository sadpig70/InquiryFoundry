//! The 5-second poll loop and the hub that parks watcher_wait callers.
//!
//! Decision S6: polling, not filesystem watching. The bus writes files as
//! .pao-*.tmp then renames, and the interaction of that pattern with watch
//! APIs is subtle enough to be a risk with no payoff — a 5s ceiling on
//! notification latency is irrelevant to this system.

use crate::bus::Bus;
use std::collections::HashMap;
use std::sync::{Arc, Condvar, Mutex};
use std::time::{Duration, Instant};

#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Counts {
    pub tasks: usize,
    pub controls: usize,
}

impl Counts {
    pub fn any(&self) -> bool {
        self.tasks > 0 || self.controls > 0
    }
}

/// One parked watcher_wait call. Duplicate waits on the same lwar_id are
/// allowed — every cell registered under the id is filled and woken.
pub struct Cell {
    slot: Mutex<Option<Counts>>,
    cv: Condvar,
}

impl Cell {
    fn new() -> Self {
        Cell {
            slot: Mutex::new(None),
            cv: Condvar::new(),
        }
    }

    pub fn fill(&self, c: Counts) {
        let mut g = self.slot.lock().unwrap();
        *g = Some(c);
        self.cv.notify_all();
    }

    /// Block until filled or the deadline passes.
    pub fn wait(&self, timeout: Duration) -> Option<Counts> {
        let deadline = Instant::now() + timeout;
        let mut g = self.slot.lock().unwrap();
        loop {
            if let Some(c) = *g {
                return Some(c);
            }
            let now = Instant::now();
            if now >= deadline {
                return None;
            }
            let (ng, _) = self.cv.wait_timeout(g, deadline - now).unwrap();
            g = ng;
        }
    }
}

#[derive(Default)]
pub struct Hub {
    waiters: Mutex<HashMap<String, Vec<Arc<Cell>>>>,
}

impl Hub {
    pub fn new() -> Self {
        Hub::default()
    }

    pub fn register(&self, lwar_id: &str) -> Arc<Cell> {
        let cell = Arc::new(Cell::new());
        self.waiters
            .lock()
            .unwrap()
            .entry(lwar_id.to_string())
            .or_default()
            .push(cell.clone());
        cell
    }

    pub fn deregister(&self, lwar_id: &str, cell: &Arc<Cell>) {
        let mut g = self.waiters.lock().unwrap();
        if let Some(v) = g.get_mut(lwar_id) {
            v.retain(|c| !Arc::ptr_eq(c, cell));
            if v.is_empty() {
                g.remove(lwar_id);
            }
        }
    }

    pub fn wake(&self, lwar_id: &str, counts: Counts) {
        if let Some(cells) = self.waiters.lock().unwrap().get(lwar_id) {
            for c in cells {
                c.fill(counts);
            }
        }
    }

    pub fn waiting_ids(&self) -> Vec<String> {
        let mut ids: Vec<String> = self.waiters.lock().unwrap().keys().cloned().collect();
        ids.sort();
        ids
    }
}

/// The poll loop body, factored out of the thread for testability.
/// Returns the ids that were woken this tick.
pub fn poll_once(bus: &Bus, hub: &Hub) -> Vec<String> {
    let mut woken = Vec::new();
    for lid in bus.watchable_lwars() {
        let (tasks, controls) = bus.counts(&lid);
        let counts = Counts { tasks, controls };
        if counts.any() {
            hub.wake(&lid, counts);
            woken.push(lid.clone());
        }
    }
    // S2(a): keep the heartbeat of every parked LWAR warm, so a busy or
    // waiting runtime stops looking identical to a dead one — the ambiguity
    // that cost a wrong diagnosis more than once.
    for lid in hub.waiting_ids() {
        bus.touch_heartbeat(&lid, "watching");
    }
    woken
}

pub fn spawn_poller(
    bus: Arc<Bus>,
    hub: Arc<Hub>,
    port: u16,
    poll_secs: u64,
    started_at: String,
) -> std::thread::JoinHandle<()> {
    std::thread::spawn(move || loop {
        let _ = poll_once(&bus, &hub);
        bus.touch_server(port, &hub.waiting_ids(), &started_at);
        std::thread::sleep(Duration::from_secs(poll_secs.max(1)));
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;

    #[test]
    fn wake_reaches_every_duplicate_waiter() {
        let hub = Hub::new();
        let a = hub.register("LWAR9");
        let b = hub.register("LWAR9");
        hub.wake("LWAR9", Counts { tasks: 2, controls: 1 });
        assert_eq!(a.wait(Duration::from_millis(50)).unwrap().tasks, 2);
        assert_eq!(b.wait(Duration::from_millis(50)).unwrap().controls, 1);
    }

    #[test]
    fn wait_times_out_empty() {
        let hub = Hub::new();
        let c = hub.register("LWAR9");
        assert!(c.wait(Duration::from_millis(30)).is_none());
        hub.deregister("LWAR9", &c);
        assert!(hub.waiting_ids().is_empty());
    }

    #[test]
    fn poll_once_wakes_only_lwars_with_mail() {
        let root = std::env::temp_dir().join(format!("pao-srv-poll-{}", std::process::id()));
        let _ = fs::remove_dir_all(&root);
        fs::create_dir_all(root.join("mailbox/LWARA/incoming")).unwrap();
        fs::create_dir_all(root.join("mailbox/LWARB/incoming")).unwrap();
        fs::write(root.join("mailbox/LWARA/incoming/001_t.json"), "{}").unwrap();
        let bus = Bus::new(root.clone());
        let hub = Hub::new();
        let a = hub.register("LWARA");
        let b = hub.register("LWARB");
        let woken = poll_once(&bus, &hub);
        assert_eq!(woken, vec!["LWARA".to_string()]);
        assert!(a.wait(Duration::from_millis(50)).is_some());
        assert!(b.wait(Duration::from_millis(30)).is_none());
        let _ = fs::remove_dir_all(root);
    }
}
