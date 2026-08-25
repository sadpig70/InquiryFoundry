//! UTC ISO8601 with microseconds, matching pao.heartbeat.v1's `last_seen`
//! (e.g. "2026-08-23T14:55:28.548684Z"). Hand-rolled so the binary carries
//! no date dependency; civil-from-days is Howard Hinnant's algorithm.

use std::time::{SystemTime, UNIX_EPOCH};

/// days since 1970-01-01 -> (year, month, day)
fn civil_from_days(z: i64) -> (i64, u32, u32) {
    let z = z + 719_468;
    let era = if z >= 0 { z } else { z - 146_096 } / 146_097;
    let doe = z - era * 146_097; // [0, 146096]
    let yoe = (doe - doe / 1460 + doe / 36524 - doe / 146_096) / 365; // [0, 399]
    let y = yoe + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100); // [0, 365]
    let mp = (5 * doy + 2) / 153; // [0, 11]
    let d = (doy - (153 * mp + 2) / 5 + 1) as u32; // [1, 31]
    let m = if mp < 10 { mp + 3 } else { mp - 9 } as u32; // [1, 12]
    (if m <= 2 { y + 1 } else { y }, m, d)
}

pub fn iso_from_micros(micros: u64) -> String {
    let secs = (micros / 1_000_000) as i64;
    let frac = micros % 1_000_000;
    let days = secs.div_euclid(86_400);
    let sod = secs.rem_euclid(86_400);
    let (y, mo, d) = civil_from_days(days);
    format!(
        "{:04}-{:02}-{:02}T{:02}:{:02}:{:02}.{:06}Z",
        y,
        mo,
        d,
        sod / 3600,
        (sod % 3600) / 60,
        sod % 60,
        frac
    )
}

pub fn now_iso() -> String {
    let micros = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_micros() as u64)
        .unwrap_or(0);
    iso_from_micros(micros)
}
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn matches_known_timestamps() {
        // datetime.datetime(2026, 8, 23, 14, 55, 28, 548684, tzinfo=utc).timestamp()
        assert_eq!(iso_from_micros(1_787_496_928_548_684), "2026-08-23T14:55:28.548684Z");
        assert_eq!(iso_from_micros(0), "1970-01-01T00:00:00.000000Z");
        // leap year day: 2024-02-29
        assert_eq!(iso_from_micros(1_709_164_800_000_000), "2024-02-29T00:00:00.000000Z");
    }
}
