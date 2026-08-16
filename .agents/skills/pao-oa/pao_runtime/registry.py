from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from . import __version__
from .common import (
    FileLock,
    atomic_write_json,
    ensure_mailbox,
    load_json,
    parse_utc,
    safe_load_json,
    utc_now,
    validate_instance_id,
    validate_lwar_id,
)
from .contracts import validate_contract


ALLOWED_TRANSITIONS = {
    "on": {"draining", "off"},
    "draining": {"on", "off"},
    "off": {"on", "deregistered"},
}


class RegistryService:
    def __init__(self, root: Path, tombstone_retention_s: int = 300):
        self.root = root.resolve()
        self.registry_path = self.root / "var" / "registry" / "lwar_registry.json"
        self.tombstones_path = self.root / "var" / "registry" / "tombstones.json"
        self.lock_path = self.root / "var" / "registry" / ".registry.lock"
        self.tombstone_retention_s = tombstone_retention_s

    def load_registry(self) -> dict[str, Any]:
        if not self.registry_path.is_file():
            return {
                "schema_version": "pao.lwar-registry-state.v1",
                "registry_version": 0,
                "allocation_strategy": "lowest_available",
                "slots": {},
                "updated_at": utc_now(),
            }
        registry = load_json(self.registry_path)
        validate_contract(registry, "registry-state.schema.json")
        return registry

    def load_tombstones(self) -> dict[str, Any]:
        if not self.tombstones_path.is_file():
            return {"schema_version": "pao.lwar-tombstones.v1", "entries": {}, "updated_at": utc_now()}
        tombstones = load_json(self.tombstones_path)
        validate_contract(tombstones, "tombstones.schema.json")
        return tombstones

    def _tombstone_blocked(self, entry: dict[str, Any] | None) -> bool:
        if not entry:
            return False
        return parse_utc(entry["reusable_after"]) > datetime.now(timezone.utc)

    def _lowest_available(self, registry: dict[str, Any], tombstones: dict[str, Any]) -> str:
        index = 1
        while True:
            candidate = f"LWAR{index}"
            if candidate not in registry["slots"] and not self._tombstone_blocked(tombstones["entries"].get(candidate)):
                return candidate
            index += 1

    def _archive_request(self, request_path: Path, category: str) -> None:
        archive = self.root / "control" / category / "archive" / request_path.name
        archive.parent.mkdir(parents=True, exist_ok=True)
        if request_path.exists():
            os.replace(request_path, archive)

    def _active_mailbox_work(self, lwar_id: str) -> dict[str, int]:
        """Count work whose loss would make identity reaping unsafe."""
        mailbox = self.root / "mailbox" / lwar_id
        active = {}
        for name in ("incoming", "claimed", "leases", "outgoing", "control", "control_claimed"):
            count = sum(1 for path in (mailbox / name).glob("*.json") if path.is_file())
            if count:
                active[name] = count
        return active

    def retire_stale(
        self,
        lwar_id: str,
        instance_id: str,
        generation: int,
        expected_last_seen: str,
        stale_after_s: float,
        reason: str,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """Retire one exact stale, idle identity with tombstone-first fencing."""
        lwar_id = validate_lwar_id(lwar_id)
        instance_id = validate_instance_id(instance_id)
        if generation <= 0:
            raise ValueError("generation must be positive")
        if stale_after_s <= 0:
            raise ValueError("stale threshold must be positive")
        try:
            parse_utc(expected_last_seen)
        except (TypeError, ValueError) as error:
            raise ValueError("expected last_seen must be a date-time") from error
        reason = reason.strip()
        if not reason:
            raise ValueError("retirement reason must be non-empty")
        if len(reason) > 500:
            raise ValueError("retirement reason must be at most 500 characters")
        observed_at = now or datetime.now(timezone.utc)

        with FileLock(self.lock_path):
            registry = self.load_registry()
            tombstones = self.load_tombstones()
            slot = registry["slots"].get(lwar_id)
            tombstone = tombstones["entries"].get(lwar_id)

            if slot is None:
                already_retired = bool(
                    tombstone
                    and tombstone.get("instance_id") == instance_id
                    and tombstone.get("last_generation") == generation
                    and tombstone.get("retirement_mode") == "stale_idle_reap"
                    and tombstone.get("expected_last_seen") == expected_last_seen
                    and tombstone.get("retirement_reason") == reason
                    and tombstone.get("stale_after_s") == stale_after_s
                )
                return {
                    "accepted": already_retired,
                    "reason": "already_retired" if already_retired else "lwar_not_registered",
                    "stale_confirmed": already_retired,
                    "heartbeat_age_s": (
                        tombstone.get("heartbeat_age_s") if already_retired else None
                    ),
                    "registry_version": registry["registry_version"],
                    "active_work": {},
                }
            if slot.get("instance_id") != instance_id or slot.get("generation") != generation:
                return {
                    "accepted": False,
                    "reason": "identity_mismatch",
                    "stale_confirmed": False,
                    "heartbeat_age_s": None,
                    "registry_version": registry["registry_version"],
                    "active_work": {},
                }
            if slot.get("state") not in {"on", "draining", "off"}:
                return {
                    "accepted": False,
                    "reason": "registry_state_not_retirable",
                    "stale_confirmed": False,
                    "heartbeat_age_s": None,
                    "registry_version": registry["registry_version"],
                    "active_work": {},
                }

            heartbeat_path = self.root / "mailbox" / lwar_id / "heartbeat.json"
            heartbeat = safe_load_json(heartbeat_path) if heartbeat_path.is_file() else None
            try:
                if heartbeat is not None:
                    validate_contract(heartbeat, "heartbeat.schema.json")
            except ValueError:
                heartbeat = None
            if heartbeat is None:
                rejection = "heartbeat_missing_or_invalid"
                age_s = None
            elif (
                heartbeat.get("instance_id") != instance_id
                or heartbeat.get("generation") != generation
            ):
                rejection = "heartbeat_identity_mismatch"
                age_s = None
            elif heartbeat.get("last_seen") != expected_last_seen:
                rejection = "heartbeat_observation_changed"
                age_s = None
            elif heartbeat.get("status") == "starting":
                rejection = "heartbeat_starting"
                age_s = None
            elif heartbeat.get("status") == "running" or heartbeat.get("current_task_id") is not None:
                rejection = "heartbeat_not_idle"
                age_s = None
            elif heartbeat.get("status") not in {
                "watching",
                "idle",
                "on",
                "draining",
                "off",
                "control",
            }:
                rejection = "heartbeat_state_not_retirable"
                age_s = None
            else:
                try:
                    age_s = max(
                        0.0,
                        (observed_at - parse_utc(heartbeat["last_seen"])).total_seconds(),
                    )
                except (KeyError, TypeError, ValueError):
                    rejection = "heartbeat_missing_or_invalid"
                    age_s = None
                else:
                    rejection = None if age_s > stale_after_s else "heartbeat_not_stale"

            stale_confirmed = rejection is None
            if rejection is not None:
                return {
                    "accepted": False,
                    "reason": rejection,
                    "stale_confirmed": False,
                    "heartbeat_age_s": age_s,
                    "registry_version": registry["registry_version"],
                    "active_work": {},
                }

            active_work = self._active_mailbox_work(lwar_id)
            if active_work:
                return {
                    "accepted": False,
                    "reason": "active_mailbox_work",
                    "stale_confirmed": stale_confirmed,
                    "heartbeat_age_s": age_s,
                    "registry_version": registry["registry_version"],
                    "active_work": active_work,
                }

            registry["registry_version"] = int(registry["registry_version"]) + 1
            registry["updated_at"] = utc_now()
            del registry["slots"][lwar_id]
            reusable_after = observed_at + timedelta(seconds=self.tombstone_retention_s)
            tombstones["entries"][lwar_id] = {
                "last_generation": generation,
                "instance_id": instance_id,
                "deregistered_at": utc_now(),
                "reusable_after": reusable_after.isoformat().replace("+00:00", "Z"),
                "retirement_mode": "stale_idle_reap",
                "retirement_reason": reason,
                "expected_last_seen": expected_last_seen,
                "stale_after_s": stale_after_s,
                "heartbeat_age_s": age_s,
            }
            tombstones["updated_at"] = utc_now()
            # Tombstone first: a crash can retain the occupied slot but can
            # never expose an unfenced generation for premature reuse.
            atomic_write_json(self.tombstones_path, tombstones)
            atomic_write_json(self.registry_path, registry)
            return {
                "accepted": True,
                "reason": None,
                "stale_confirmed": True,
                "heartbeat_age_s": age_s,
                "registry_version": registry["registry_version"],
                "active_work": {},
            }

    def reclaim_unadopted(
        self,
        lwar_id: str,
        instance_id: str,
        generation: int,
        unadopted_after_s: float,
        reason: str,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """Reclaim one approved slot whose identity was never adopted.

        Adoption is what writes the first current-generation heartbeat, so both
        `retire_stale` and `reap_startup` — which each require one — are
        structurally unreachable for a slot that never started. This is the
        fenced path for exactly that state, and it refuses any slot that shows
        evidence of having started.
        """
        lwar_id = validate_lwar_id(lwar_id)
        instance_id = validate_instance_id(instance_id)
        if generation <= 0:
            raise ValueError("generation must be positive")
        if unadopted_after_s <= 0:
            raise ValueError("unadopted threshold must be positive")
        reason = reason.strip()
        if not reason:
            raise ValueError("reclaim reason must be non-empty")
        if len(reason) > 500:
            raise ValueError("reclaim reason must be at most 500 characters")
        observed_at = now or datetime.now(timezone.utc)

        with FileLock(self.lock_path):
            registry = self.load_registry()
            tombstones = self.load_tombstones()
            slot = registry["slots"].get(lwar_id)
            tombstone = tombstones["entries"].get(lwar_id)

            if slot is None:
                already_reclaimed = bool(
                    tombstone
                    and tombstone.get("instance_id") == instance_id
                    and tombstone.get("last_generation") == generation
                    and tombstone.get("retirement_mode") == "unadopted_reap"
                    and tombstone.get("retirement_reason") == reason
                    and tombstone.get("unadopted_after_s") == unadopted_after_s
                )
                return {
                    "accepted": already_reclaimed,
                    "reason": "already_reclaimed" if already_reclaimed else "lwar_not_registered",
                    "unadopted_confirmed": already_reclaimed,
                    "approval_age_s": (
                        tombstone.get("approval_age_s") if already_reclaimed else None
                    ),
                    "registry_version": registry["registry_version"],
                    "active_work": {},
                }
            if slot.get("instance_id") != instance_id or slot.get("generation") != generation:
                return {
                    "accepted": False,
                    "reason": "identity_mismatch",
                    "unadopted_confirmed": False,
                    "approval_age_s": None,
                    "registry_version": registry["registry_version"],
                    "active_work": {},
                }
            if slot.get("state") not in {"on", "draining", "off"}:
                return {
                    "accepted": False,
                    "reason": "registry_state_not_retirable",
                    "unadopted_confirmed": False,
                    "approval_age_s": None,
                    "registry_version": registry["registry_version"],
                    "active_work": {},
                }

            # Adoption fence. Any readable heartbeat bound to this exact
            # identity proves the runtime did start; that slot belongs to
            # retire_stale or reap_startup, never here.
            heartbeat_path = self.root / "mailbox" / lwar_id / "heartbeat.json"
            heartbeat = safe_load_json(heartbeat_path) if heartbeat_path.is_file() else None
            try:
                if heartbeat is not None:
                    validate_contract(heartbeat, "heartbeat.schema.json")
            except ValueError:
                heartbeat = None
            if (
                heartbeat is not None
                and heartbeat.get("instance_id") == instance_id
                and heartbeat.get("generation") == generation
            ):
                return {
                    "accepted": False,
                    "reason": "identity_already_adopted",
                    "unadopted_confirmed": False,
                    "approval_age_s": None,
                    "registry_version": registry["registry_version"],
                    "active_work": {},
                }

            try:
                approval_age_s = max(
                    0.0,
                    (observed_at - parse_utc(slot["registered_at"])).total_seconds(),
                )
            except (KeyError, TypeError, ValueError):
                return {
                    "accepted": False,
                    "reason": "registered_at_missing_or_invalid",
                    "unadopted_confirmed": False,
                    "approval_age_s": None,
                    "registry_version": registry["registry_version"],
                    "active_work": {},
                }
            if approval_age_s <= unadopted_after_s:
                return {
                    "accepted": False,
                    "reason": "approval_too_recent",
                    "unadopted_confirmed": False,
                    "approval_age_s": approval_age_s,
                    "registry_version": registry["registry_version"],
                    "active_work": {},
                }

            active_work = self._active_mailbox_work(lwar_id)
            if active_work:
                return {
                    "accepted": False,
                    "reason": "active_mailbox_work",
                    "unadopted_confirmed": True,
                    "approval_age_s": approval_age_s,
                    "registry_version": registry["registry_version"],
                    "active_work": active_work,
                }

            registry["registry_version"] = int(registry["registry_version"]) + 1
            registry["updated_at"] = utc_now()
            del registry["slots"][lwar_id]
            reusable_after = observed_at + timedelta(seconds=self.tombstone_retention_s)
            tombstones["entries"][lwar_id] = {
                "last_generation": generation,
                "instance_id": instance_id,
                "deregistered_at": utc_now(),
                "reusable_after": reusable_after.isoformat().replace("+00:00", "Z"),
                "retirement_mode": "unadopted_reap",
                "retirement_reason": reason,
                "unadopted_after_s": unadopted_after_s,
                "approval_age_s": approval_age_s,
            }
            tombstones["updated_at"] = utc_now()
            # Tombstone first, exactly as the other two reclaim paths: an
            # interruption may leave the slot occupied but never unfenced.
            atomic_write_json(self.tombstones_path, tombstones)
            atomic_write_json(self.registry_path, registry)
            return {
                "accepted": True,
                "reason": None,
                "unadopted_confirmed": True,
                "approval_age_s": approval_age_s,
                "registry_version": registry["registry_version"],
                "active_work": {},
            }

    def expire_pending_control(
        self,
        lwar_id: str,
        instance_id: str,
        generation: int,
        older_than_s: float,
        reason: str,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """Expire controls left undeliverable in front of a dead watcher.

        A control is claimed by the watcher, so one published to a runtime that
        never comes back is never consumed. `prune` does not touch pending
        `control/`, and `retire_stale` requires it to be empty, so a `shutdown`
        sent to stop a watcher can permanently block reclaiming its slot.

        The original bytes are preserved: each control is moved unchanged into
        `archive/control/` next to a `.expired.json` sidecar recording why.
        """
        lwar_id = validate_lwar_id(lwar_id)
        instance_id = validate_instance_id(instance_id)
        if generation <= 0:
            raise ValueError("generation must be positive")
        if older_than_s <= 0:
            raise ValueError("control expiry threshold must be positive")
        reason = reason.strip()
        if not reason:
            raise ValueError("expiry reason must be non-empty")
        if len(reason) > 500:
            raise ValueError("expiry reason must be at most 500 characters")
        observed_at = now or datetime.now(timezone.utc)

        with FileLock(self.lock_path):
            registry = self.load_registry()
            slot = registry["slots"].get(lwar_id)
            if slot is None:
                return {"accepted": False, "reason": "lwar_not_registered", "expired": []}
            if slot.get("instance_id") != instance_id or slot.get("generation") != generation:
                return {"accepted": False, "reason": "identity_mismatch", "expired": []}

            # Liveness fence: a watcher whose heartbeat is fresh will still
            # claim these controls, so expiring them would drop real delivery.
            heartbeat_path = self.root / "mailbox" / lwar_id / "heartbeat.json"
            heartbeat = safe_load_json(heartbeat_path) if heartbeat_path.is_file() else None
            try:
                if heartbeat is not None:
                    validate_contract(heartbeat, "heartbeat.schema.json")
            except ValueError:
                heartbeat = None
            if (
                heartbeat is not None
                and heartbeat.get("instance_id") == instance_id
                and heartbeat.get("generation") == generation
            ):
                try:
                    heartbeat_age_s = max(
                        0.0,
                        (observed_at - parse_utc(heartbeat["last_seen"])).total_seconds(),
                    )
                except (KeyError, TypeError, ValueError):
                    heartbeat_age_s = None
                if heartbeat_age_s is None or heartbeat_age_s <= older_than_s:
                    return {
                        "accepted": False,
                        "reason": "watcher_alive",
                        "heartbeat_age_s": heartbeat_age_s,
                        "expired": [],
                    }

            control_dir = self.root / "mailbox" / lwar_id / "control"
            archive_dir = self.root / "mailbox" / lwar_id / "archive" / "control"
            expired: list[dict[str, Any]] = []
            skipped: list[dict[str, Any]] = []
            for path in sorted(control_dir.glob("*.json")):
                if not path.is_file():
                    continue
                try:
                    age_s = max(
                        0.0,
                        (
                            observed_at
                            - datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
                        ).total_seconds(),
                    )
                except OSError:
                    continue
                if age_s <= older_than_s:
                    skipped.append({"file": path.name, "age_s": age_s, "reason": "too_recent"})
                    continue
                control = safe_load_json(path)
                archive_dir.mkdir(parents=True, exist_ok=True)
                sidecar = archive_dir / f"{path.stem}.expired.json"
                atomic_write_json(
                    sidecar,
                    {
                        "schema_version": "pao.control-expiry.v1",
                        "lwar_id": lwar_id,
                        "instance_id": instance_id,
                        "generation": generation,
                        "control_id": (control or {}).get("control_id"),
                        "command": (control or {}).get("command"),
                        "control_age_s": age_s,
                        "older_than_s": older_than_s,
                        "expiry_reason": reason,
                        "expired_at": utc_now(),
                    },
                )
                os.replace(path, archive_dir / path.name)
                expired.append(
                    {
                        "file": path.name,
                        "control_id": (control or {}).get("control_id"),
                        "command": (control or {}).get("command"),
                        "age_s": age_s,
                    }
                )
            return {
                "accepted": True,
                "reason": None,
                "expired": expired,
                "skipped": skipped,
            }

    def reap_startup(
        self,
        lwar_id: str,
        instance_id: str,
        generation: int,
        startup_deadline_s: float,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """Reclaim one orphaned startup slot with identity and state fencing.

        This is deliberately operator-directed. The current slot, heartbeat,
        deadline, and mailbox are all rechecked while the registry lock is held
        so a stale status observation cannot reclaim a replacement generation.
        """
        lwar_id = validate_lwar_id(lwar_id)
        instance_id = validate_instance_id(instance_id)
        if generation <= 0:
            raise ValueError("generation must be positive")
        if startup_deadline_s <= 0:
            raise ValueError("startup deadline must be positive")
        observed_at = now or datetime.now(timezone.utc)

        with FileLock(self.lock_path):
            registry = self.load_registry()
            tombstones = self.load_tombstones()
            slot = registry["slots"].get(lwar_id)
            tombstone = tombstones["entries"].get(lwar_id)

            if slot is None:
                already_reaped = bool(
                    tombstone
                    and tombstone.get("instance_id") == instance_id
                    and tombstone.get("last_generation") == generation
                )
                return {
                    "accepted": already_reaped,
                    "reason": "already_reaped" if already_reaped else "lwar_not_registered",
                    "deadline_missed": already_reaped,
                    "registry_version": registry["registry_version"],
                    "active_work": {},
                }
            if slot.get("instance_id") != instance_id or slot.get("generation") != generation:
                return {
                    "accepted": False,
                    "reason": "identity_mismatch",
                    "deadline_missed": False,
                    "registry_version": registry["registry_version"],
                    "active_work": {},
                }

            heartbeat_path = self.root / "mailbox" / lwar_id / "heartbeat.json"
            heartbeat = safe_load_json(heartbeat_path) if heartbeat_path.is_file() else None
            try:
                if heartbeat is not None:
                    validate_contract(heartbeat, "heartbeat.schema.json")
            except ValueError:
                heartbeat = None
            if heartbeat is None:
                reason = "heartbeat_missing_or_invalid"
                age_s = None
            elif (
                heartbeat.get("instance_id") != instance_id
                or heartbeat.get("generation") != generation
            ):
                reason = "heartbeat_identity_mismatch"
                age_s = None
            elif heartbeat.get("status") != "starting":
                reason = "heartbeat_not_starting"
                age_s = None
            else:
                try:
                    age_s = max(0.0, (observed_at - parse_utc(heartbeat["last_seen"])).total_seconds())
                except (KeyError, TypeError, ValueError):
                    reason = "heartbeat_missing_or_invalid"
                    age_s = None
                else:
                    reason = None if age_s > startup_deadline_s else "startup_deadline_not_missed"

            deadline_missed = reason is None
            if reason is not None:
                return {
                    "accepted": False,
                    "reason": reason,
                    "deadline_missed": False,
                    "heartbeat_age_s": age_s,
                    "registry_version": registry["registry_version"],
                    "active_work": {},
                }

            active_work = self._active_mailbox_work(lwar_id)
            if active_work:
                return {
                    "accepted": False,
                    "reason": "active_mailbox_work",
                    "deadline_missed": deadline_missed,
                    "heartbeat_age_s": age_s,
                    "registry_version": registry["registry_version"],
                    "active_work": active_work,
                }

            registry["registry_version"] = int(registry["registry_version"]) + 1
            registry["updated_at"] = utc_now()
            del registry["slots"][lwar_id]
            reusable_after = observed_at + timedelta(seconds=self.tombstone_retention_s)
            tombstones["entries"][lwar_id] = {
                "last_generation": generation,
                "instance_id": instance_id,
                "deregistered_at": utc_now(),
                "reusable_after": reusable_after.isoformat().replace("+00:00", "Z"),
            }
            tombstones["updated_at"] = utc_now()
            # Tombstone first: an interruption can temporarily retain an
            # occupied slot, but can never expose an unfenced free slot.
            atomic_write_json(self.tombstones_path, tombstones)
            atomic_write_json(self.registry_path, registry)
            return {
                "accepted": True,
                "reason": None,
                "deadline_missed": True,
                "heartbeat_age_s": age_s,
                "registry_version": registry["registry_version"],
                "active_work": {},
            }

    def process_registration(self, request_path: Path) -> dict[str, Any]:
        request = load_json(request_path)
        validate_contract(request, "registration-request.schema.json")
        request_id = request["request_id"]
        instance_id = validate_instance_id(request["instance_id"])
        response_path = self.root / "control" / "registration" / "responses" / f"{request_id}.json"
        if response_path.is_file():
            self._archive_request(request_path, "registration")
            return load_json(response_path)

        accepted = False
        reason = None
        lwar_id = None
        generation = None
        registry_version = None
        state = "unregistered"

        # v1 handshake: every schema-valid request is stamped. A mismatched
        # bundle is rejected before both fresh allocation and idempotent replay.
        request_version = request["runtime_version"]
        version_mismatch = request_version != __version__

        with FileLock(self.lock_path):
            registry = self.load_registry()
            tombstones = self.load_tombstones()
            # Idempotent replay: a prior reconcile committed the registry
            # mutation but crashed before writing the response. This instance is
            # already in a slot (one instance_id ⇒ one slot), so reconstruct its
            # response instead of allocating a SECOND slot for the same instance.
            existing_id = next(
                (lid for lid, s in registry["slots"].items() if s.get("instance_id") == instance_id),
                None,
            )
            if version_mismatch:
                reason = "runtime_version_mismatch"
            elif existing_id is not None:
                existing = registry["slots"][existing_id]
                accepted = True
                lwar_id = existing_id
                generation = existing["generation"]
                registry_version = registry["registry_version"]
                state = existing["state"]
                candidate = existing_id
            else:
                requested = request.get("requested_lwar_id")
                if requested is not None:
                    validate_lwar_id(requested)
                    candidate = requested
                else:
                    candidate = self._lowest_available(registry, tombstones)

                if candidate in registry["slots"]:
                    reason = "lwar_id_in_use"
                elif self._tombstone_blocked(tombstones["entries"].get(candidate)):
                    reason = "lwar_id_tombstoned"
                else:
                    previous = tombstones["entries"].get(candidate, {})
                    generation = int(previous.get("last_generation", 0)) + 1
                    registry["registry_version"] = int(registry["registry_version"]) + 1
                    registry_version = registry["registry_version"]
                    registry["updated_at"] = utc_now()
                    registry["slots"][candidate] = {
                        "instance_id": instance_id,
                        "generation": generation,
                        "state": "on",
                        "profile": request["profile"],
                        "registered_at": utc_now(),
                        "last_seen": None,
                    }
                    tombstones["entries"].pop(candidate, None)
                    tombstones["updated_at"] = utc_now()
                    atomic_write_json(self.registry_path, registry)
                    atomic_write_json(self.tombstones_path, tombstones)
                    ensure_mailbox(self.root, candidate)
                    accepted = True
                    lwar_id = candidate
                    state = "on"

        response = {
            "schema_version": "pao.lwar-registration-response.v1",
            "request_id": request_id,
            "instance_id": instance_id,
            "accepted": accepted,
            "lwar_id": lwar_id,
            "generation": generation,
            "registry_version": registry_version,
            "state": state,
            "behavior_contract": "lwar-runtime.v2-adp",
            "reason": reason,
            "decided_at": utc_now(),
        }
        validate_contract(response, "registration-response.schema.json")
        atomic_write_json(response_path, response)
        self._archive_request(request_path, "registration")
        return response

    def process_lifecycle(self, request_path: Path) -> dict[str, Any]:
        request = load_json(request_path)
        validate_contract(request, "lifecycle-request.schema.json")
        request_id = request["request_id"]
        lwar_id = validate_lwar_id(request["lwar_id"])
        instance_id = validate_instance_id(request["instance_id"])
        response_path = self.root / "control" / "lifecycle" / "responses" / f"{request_id}.json"
        if response_path.is_file():
            self._archive_request(request_path, "lifecycle")
            return load_json(response_path)

        accepted = False
        reason = None
        previous_state = "off"
        resulting_state = "off"
        registry_version = None

        with FileLock(self.lock_path):
            registry = self.load_registry()
            tombstones = self.load_tombstones()
            slot = registry["slots"].get(lwar_id)
            requested_state = request["requested_state"]
            tomb = tombstones["entries"].get(lwar_id)
            if slot is None and requested_state == "deregistered" and tomb is not None and (
                tomb.get("instance_id") == instance_id
                and tomb.get("last_generation") == request["generation"]
            ):
                # Idempotent replay of a committed deregister: the slot is gone
                # and a matching tombstone exists (crash before the response).
                accepted = True
                previous_state = "off"
                resulting_state = "deregistered"
                registry_version = registry["registry_version"]
            elif slot is None:
                reason = "lwar_not_registered"
            elif slot["instance_id"] != instance_id or slot["generation"] != request["generation"]:
                reason = "identity_mismatch"
            elif slot["state"] == requested_state:
                # Idempotent replay: the transition already applied (crash before
                # the response was written); re-affirm it rather than rejecting
                # it as an invalid same-state transition.
                accepted = True
                previous_state = requested_state
                resulting_state = requested_state
                registry_version = registry["registry_version"]
            else:
                previous_state = slot["state"]
                resulting_state = previous_state
                if requested_state not in ALLOWED_TRANSITIONS.get(previous_state, set()):
                    reason = "invalid_transition"
                else:
                    registry["registry_version"] = int(registry["registry_version"]) + 1
                    registry_version = registry["registry_version"]
                    registry["updated_at"] = utc_now()
                    resulting_state = requested_state
                    if requested_state == "deregistered":
                        del registry["slots"][lwar_id]
                        reusable_after = datetime.now(timezone.utc) + timedelta(seconds=self.tombstone_retention_s)
                        tombstones["entries"][lwar_id] = {
                            "last_generation": request["generation"],
                            "instance_id": instance_id,
                            "deregistered_at": utc_now(),
                            "reusable_after": reusable_after.isoformat().replace("+00:00", "Z"),
                        }
                        tombstones["updated_at"] = utc_now()
                        atomic_write_json(self.tombstones_path, tombstones)
                    else:
                        slot["state"] = requested_state
                    atomic_write_json(self.registry_path, registry)
                    accepted = True

        response = {
            "schema_version": "pao.lwar-lifecycle-response.v1",
            "request_id": request_id,
            "lwar_id": lwar_id,
            "instance_id": instance_id,
            "generation": request["generation"],
            "accepted": accepted,
            "previous_state": previous_state,
            "resulting_state": resulting_state,
            "registry_version": registry_version,
            "reason": reason,
            "decided_at": utc_now(),
        }
        validate_contract(response, "lifecycle-response.schema.json")
        atomic_write_json(response_path, response)
        self._archive_request(request_path, "lifecycle")
        return response

    def _quarantine_request(self, request_path: Path, category: str, error: object) -> None:
        """Move a request that could not be processed (corrupt JSON, missing
        required field, ...) into `control/<category>/failed/` so one poison
        request can never wedge every future reconcile at the same spot."""
        failed = self.root / "control" / category / "failed" / request_path.name
        failed.parent.mkdir(parents=True, exist_ok=True)
        if not request_path.exists():
            return
        try:
            os.replace(request_path, failed)
        except OSError:
            return
        try:
            atomic_write_json(
                failed.with_suffix(".error.json"),
                {"reason": f"reconcile_error:{error}", "failed_at": utc_now()},
            )
        except OSError:
            pass

    def reconcile(self) -> dict[str, int]:
        registration_dir = self.root / "control" / "registration" / "requests"
        lifecycle_dir = self.root / "control" / "lifecycle" / "requests"
        registration_dir.mkdir(parents=True, exist_ok=True)
        lifecycle_dir.mkdir(parents=True, exist_ok=True)
        registrations = 0
        lifecycles = 0
        quarantined = 0
        for path in sorted(registration_dir.glob("*.json")):
            try:
                self.process_registration(path)
                registrations += 1
            except Exception as error:  # noqa: BLE001 — one bad request must not wedge the sweep
                self._quarantine_request(path, "registration", error)
                quarantined += 1
        for path in sorted(lifecycle_dir.glob("*.json")):
            try:
                self.process_lifecycle(path)
                lifecycles += 1
            except Exception as error:  # noqa: BLE001
                self._quarantine_request(path, "lifecycle", error)
                quarantined += 1
        return {"registrations": registrations, "lifecycles": lifecycles, "quarantined": quarantined}
