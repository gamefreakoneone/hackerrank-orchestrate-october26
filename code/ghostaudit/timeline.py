"""Resource state at audit_at (spec 0010): latest establishing observation, absence by snapshot omission,
state-check activity fallback. Operational activity claims never set state."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime

from ghostaudit.evidence.derive import config
from ghostaudit.evidence.index import Ledger, eligible
from ghostaudit.evidence.model import Observation, SnapshotCoverage
from ghostaudit.identity import Subject

ABSENT_RESULTS = {"NOT_FOUND", "MISS", "ABSENT", "DELETED"}
PRESENT_EVENT_SUFFIXES = ("_pii_scan", "_identity_scan", "heartbeat", "config_loaded", "_evaluated",
                          "authorization_completed", "_loaded", "deletion_marker_check", "message_read",
                          "analytics_profile_read", "thumbnail_failed")
REPLICA_FREE_COPIES = {"primary", "bundle"}


def observed_presence(observation: Observation) -> str | None:
    """'present' | 'absent' | None (the observation says nothing about existence)."""
    fields = observation.fields
    if observation.source_kind in ("sql", "png", "pdf", "activity"):
        return "present"
    for key in ("status_code", "http_status"):
        if fields.get(key) == "404":
            return "absent"
        if fields.get(key) in ("200", "201"):
            return "present"
    if (fields.get("result") or "").upper() in ABSENT_RESULTS:
        return "absent"
    if fields.get("rows") == "0" or fields.get("total_hits") == "0" or fields.get("hits.total") == "0":
        return "absent"
    if observation.source_kind in ("json", "txt"):
        return "present"
    if fields.get("rows") not in (None, "0") or fields.get("result") or fields.get("total_hits") not in (None, "0"):
        return "present"
    events = (fields.get("events") or "").split(",")
    if any(event.endswith(PRESENT_EVENT_SUFFIXES) or event.endswith("_completed") for event in events):
        return "present"
    if fields.get("enabled") or fields.get("restore_allowed") or fields.get("eligible"):
        return "present"
    return None


def observed_enabled(observation: Observation) -> bool | None:
    fields = observation.fields
    if fields.get("enabled") in ("true", "false"):
        return fields["enabled"] == "true"
    result = (fields.get("result") or "").upper()
    if observation.category == "DATA_FLOW" and result in ("ACTIVE", "DISABLED"):
        return result == "ACTIVE"
    return None


def observed_restorable(observation: Observation) -> bool | None:
    fields = observation.fields
    if fields.get("restore_allowed") in ("true", "false"):
        return fields["restore_allowed"] == "true"
    if fields.get("deletion_block") == "true":
        return False
    if fields.get("eligible") in ("true", "false") and fields.get("deletion_block") in ("false", None):
        return fields["eligible"] == "true"
    if fields.get("decision") in ("deny", "allow"):
        return fields["decision"] == "allow"
    result = (fields.get("result") or "").upper()
    if observation.category == "BACKUP_ARCHIVE" and result in ("ACTIVE", "BLOCKED"):
        return result == "ACTIVE"
    return None


def _name_in_text(name: str, text: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(name)}(?!\w)", unicodedata.normalize("NFC", text)) is not None


def exposed_direct_identifiers(observation: Observation, subject: Subject) -> set[str]:
    """Subject direct identifiers (email, phone, name, email hash) still present in the record; user_id excluded."""
    direct = subject.emails | subject.phones | subject.names | subject.email_hashes
    exposed = set(observation.identifiers & direct)
    name_fields = set(config()["name_fields"])
    for key, value in observation.fields.items():
        if value and key.rsplit(".", 1)[-1] not in name_fields:
            exposed |= {name for name in subject.names if _name_in_text(name, value)}
    result = (observation.fields.get("result") or "").upper()
    if result == "IDENTIFIABLE" or observation.fields.get("direct_identifiers") not in (None, "0"):
        exposed.add("(reported identifiable)")
    return exposed


def has_user_link(observation: Observation, subject: Subject) -> bool:
    return subject.user_id is not None and subject.user_id in observation.identifiers


@dataclass(frozen=True)
class Fact:
    value: object                     # 'present'/'absent', or bool for enabled / restorable
    proof: str                        # evidence_id (file, coverage file or activity id)
    proof_kind: str                   # "file" | "activity"
    observation: Observation | None   # None for absence by snapshot omission
    rule: str                         # how it was established


def _latest(observations: list[Observation], extract, prefer) -> Fact | None:
    """Latest file observation with a value; within one capture, `prefer` wins (any copy present / active)."""
    files = [o for o in observations if o.source_kind != "activity"]
    valued = [(o, extract(o)) for o in files if extract(o) is not None]
    if not valued:
        return None
    latest_key = max((o.captured_at, o.evidence_id) for o, _ in valued)
    same_capture = [(o, v) for o, v in valued if (o.captured_at, o.evidence_id) == latest_key]
    same_capture.sort(key=lambda ov: (ov[1] == prefer, ov[0].observed_at or ov[0].captured_at), reverse=True)
    observation, value = same_capture[0]
    return Fact(value, observation.evidence_id, "file", observation, "observed")


def _state_check(observations: list[Observation], extract) -> Fact | None:
    checks = [o for o in observations if o.source_kind == "activity" and extract(o) is not None]
    if not checks:
        return None
    latest = max(checks, key=lambda o: (o.captured_at, o.evidence_id))
    return Fact(extract(latest), latest.evidence_id, "activity", latest, "state_check_activity")


def absence_by_omission(resource_id: str, system_id: str | None, category: str | None, audit_at: datetime,
                        ledger: Ledger, last_delete_at: datetime | None,
                        required_copy: str | None = None) -> SnapshotCoverage | None:
    """TECHNICAL_DESIGN §5 Q2 rule: eligible coverage of the resource's collection omitting it; drop snapshots
    captured at or before the last DELETE_RECORD claim; latest with replica coverage, else latest; else None.
    `required_copy`: the replica where the resource was last seen; only a snapshot of that copy can show it gone."""
    container_category = config()["container_category"]
    candidates = [c for c in ledger.coverage_by_system.get(system_id or "", [])
                  if eligible(c, audit_at) and container_category.get(c.collection) == category
                  and resource_id not in c.resource_ids
                  and (last_delete_at is None or c.captured_at > last_delete_at)
                  and (required_copy is None or c.physical_copy == required_copy)]
    if not candidates:
        return None
    by_file: dict[str, list[SnapshotCoverage]] = {}
    for coverage in candidates:
        by_file.setdefault(coverage.file_id, []).append(coverage)
    # a file counts only if no other copy in that same file holds the resource (any copy present ⇒ present)
    files = {f: rows for f, rows in by_file.items()
             if not any(resource_id in c.resource_ids for c in ledger.coverage if c.file_id == f)}
    if not files:
        return None
    with_replica = {f: rows for f, rows in files.items() if any(c.physical_copy not in REPLICA_FREE_COPIES
                                                                for c in rows)}
    pool = with_replica or files
    chosen_file = max(pool, key=lambda f: (pool[f][0].captured_at, f))
    return pool[chosen_file][0]


@dataclass(frozen=True)
class ResourceState:
    resource_id: str
    presence: Fact | None
    enabled: Fact | None
    restorable: Fact | None
    observations: tuple[Observation, ...]


def state_at(resource_id: str, system_id: str | None, category: str | None, audit_at: datetime, ledger: Ledger,
             last_delete_at: datetime | None) -> ResourceState:
    observations = [o for o in ledger.by_resource.get(resource_id, []) if eligible(o, audit_at)]
    presence = _latest(observations, observed_presence, "present")
    if presence is None or presence.value == "present":   # an observed absence is cited as observed (rule 1)
        seen = presence.observation if presence else None
        replica_seen = (seen.physical_copy if seen is not None and seen.source_kind == "sql"
                        and seen.physical_copy not in REPLICA_FREE_COPIES else None)
        omission = absence_by_omission(resource_id, system_id, category, audit_at, ledger, last_delete_at,
                                       required_copy=replica_seen)
        if omission is not None and (presence is None or omission.captured_at > presence.observation.captured_at):
            presence = Fact("absent", omission.file_id, "file", None, "snapshot_omission")
    if presence is None:
        presence = _state_check(observations, observed_presence)
    enabled = _latest(observations, observed_enabled, True) or _state_check(observations, observed_enabled)
    restorable = _latest(observations, observed_restorable, True) or _state_check(observations, observed_restorable)
    return ResourceState(resource_id, presence, enabled, restorable, tuple(observations))


def resource_category(resource_id: str, audit_at: datetime, ledger: Ledger) -> str | None:
    """Category of the latest eligible observation that has one (the record decides, not the system)."""
    observations = [o for o in ledger.by_resource.get(resource_id, []) if eligible(o, audit_at) and o.category]
    if observations:
        return max(observations, key=lambda o: (o.captured_at, o.evidence_id)).category
    return "USER_PROFILE" if resource_id.startswith("account_") else None


def delete_claim_times(activity: list) -> dict[str, list[datetime]]:
    """resource_id -> sorted DELETE_RECORD claim times (claims only: used to supersede older snapshots)."""
    times: dict[str, list[datetime]] = {}
    for event in activity:
        if event.event_type == "DELETE_RECORD":
            times.setdefault(event.resource_id, []).append(event.event_time)
    return {rid: sorted(ts) for rid, ts in times.items()}


def last_delete_before(times: dict[str, list[datetime]], resource_id: str, audit_at: datetime) -> datetime | None:
    return max((t for t in times.get(resource_id, []) if t <= audit_at), default=None)
