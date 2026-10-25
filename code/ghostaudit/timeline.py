"""Resource state at audit_at (specs 0010, 0017): per storage copy, the latest establishing observation or a later
snapshot of that copy omitting the resource; state-check activity fallback. Operational claims never set state."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime

from ghostaudit.evidence.derive import config
from ghostaudit.evidence.index import Ledger, eligible, state_observed_at
from ghostaudit.evidence.model import Observation, SnapshotCoverage
from ghostaudit.identity import Subject

ABSENT_RESULTS = {"NOT_FOUND", "MISS", "ABSENT", "DELETED"}
PRESENT_EVENT_SUFFIXES = ("_pii_scan", "_identity_scan", "heartbeat", "config_loaded", "_evaluated",
                          "authorization_completed", "_loaded", "deletion_marker_check", "message_read",
                          "analytics_profile_read", "thumbnail_failed")


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


# Evidence-format labels carry no storage-copy identity: a service read, export, bundle, screen or document reads
# the logical service, i.e. its system of record. Only SQL table names identify replicas (sql.split_table).
SYSTEM_OF_RECORD_COPY = "primary"
EVIDENCE_FORMAT_LABELS = frozenset({"export", "bundle", "service_read", "screen", "document", "claim"})


def storage_copy(physical_copy_label: str) -> str:
    return SYSTEM_OF_RECORD_COPY if physical_copy_label in EVIDENCE_FORMAT_LABELS else physical_copy_label


@dataclass(frozen=True)
class Fact:
    value: object                     # 'present'/'absent', or bool for enabled / restorable
    proof: str                        # evidence_id (file, coverage file or activity id)
    proof_kind: str                   # "file" | "activity"
    observation: Observation | None   # None for absence by snapshot omission
    rule: str                         # observed | snapshot_omission | state_check_activity
    physical_copy: str                # storage copy the fact describes
    observed_at: datetime             # observation time used to order facts


def latest_fact_by_physical_copy(observations: list[Observation], extract, prefer) -> dict[str, Fact]:
    """Per storage copy, the latest file observation with a value: observation time, then file availability;
    on an exact tie `prefer` (present / active) wins."""
    latest: dict[str, tuple[tuple, Fact]] = {}
    for observation in observations:
        value = extract(observation) if observation.source_kind != "activity" else None
        if value is None:
            continue
        copy = storage_copy(observation.physical_copy)
        when = state_observed_at(observation)
        key = (when, observation.captured_at, observation.evidence_id, value == prefer)
        if copy not in latest or key > latest[copy][0]:
            latest[copy] = (key, Fact(value, observation.evidence_id, "file", observation, "observed", copy, when))
    return {copy: fact for copy, (_, fact) in sorted(latest.items())}


def _state_check(observations: list[Observation], extract) -> dict[str, Fact]:
    checks = [o for o in observations if o.source_kind == "activity" and extract(o) is not None]
    if not checks:
        return {}
    latest = max(checks, key=lambda o: (o.captured_at, o.evidence_id))
    return {"activity": Fact(extract(latest), latest.evidence_id, "activity", latest, "state_check_activity",
                             "activity", latest.captured_at)}


def _omitting_coverage(resource_id: str, system_id: str | None, category: str | None, audit_at: datetime,
                       ledger: Ledger, last_delete_at: datetime | None,
                       subject_user_id: str | None) -> list[SnapshotCoverage]:
    """Eligible coverage of the resource's collection that omits it, not superseded by a later DELETE_RECORD claim;
    a subject-limited bundle counts only for the subjects it was exported for."""
    container_category = config()["container_category"]
    return [c for c in ledger.coverage_by_system.get(system_id or "", [])
            if eligible(c, audit_at) and container_category.get(c.collection) == category
            and resource_id not in c.resource_ids and (last_delete_at is None or c.captured_at > last_delete_at)
            and (c.covered_subjects is None or subject_user_id in c.covered_subjects)]


def absence_by_omission(resource_id: str, system_id: str | None, category: str | None, audit_at: datetime,
                        ledger: Ledger, last_delete_at: datetime | None,
                        subject_user_id: str | None) -> SnapshotCoverage | None:
    """Never-observed resource (TECHNICAL_DESIGN §5 Q2): among files where no copy holds it, the latest file with
    replica coverage, else the latest; no surviving candidate ⇒ None (UNKNOWN)."""
    by_file: dict[str, list[SnapshotCoverage]] = {}
    for coverage in _omitting_coverage(resource_id, system_id, category, audit_at, ledger, last_delete_at,
                                       subject_user_id):
        by_file.setdefault(coverage.file_id, []).append(coverage)
    files = {f: rows for f, rows in by_file.items()
             if not any(resource_id in c.resource_ids for c in ledger.coverage if c.file_id == f)}
    if not files:
        return None
    with_replica = {f: rows for f, rows in files.items()
                    if any(storage_copy(c.physical_copy) != SYSTEM_OF_RECORD_COPY for c in rows)}
    pool = with_replica or files
    chosen_file = max(pool, key=lambda f: (pool[f][0].captured_at, f))
    return pool[chosen_file][0]


def presence_by_physical_copy(resource_id: str, system_id: str | None, category: str | None, audit_at: datetime,
                              ledger: Ledger, last_delete_at: datetime | None, subject_user_id: str | None,
                              observations: list[Observation]) -> dict[str, Fact]:
    """Latest presence per storage copy. A copy last seen present is cleared only by a later snapshot of that same
    copy omitting the resource; other copies and format-only labels never clear it."""
    facts = latest_fact_by_physical_copy(observations, observed_presence, "present")
    omitting = _omitting_coverage(resource_id, system_id, category, audit_at, ledger, last_delete_at,
                                  subject_user_id)
    for copy, fact in list(facts.items()):
        if fact.value != "present":
            continue
        later = [c for c in omitting
                 if storage_copy(c.physical_copy) == copy and state_observed_at(c) > fact.observed_at]
        if later:
            omission = max(later, key=lambda c: (state_observed_at(c), c.captured_at, c.file_id))
            facts[copy] = Fact("absent", omission.file_id, "file", None, "snapshot_omission", copy,
                               state_observed_at(omission))
    if not facts:
        omission = absence_by_omission(resource_id, system_id, category, audit_at, ledger, last_delete_at,
                                       subject_user_id)
        if omission is not None:
            copy = storage_copy(omission.physical_copy)
            facts[copy] = Fact("absent", omission.file_id, "file", None, "snapshot_omission", copy,
                               state_observed_at(omission))
    return facts or _state_check(observations, observed_presence)


@dataclass(frozen=True)
class ResourceState:
    resource_id: str
    presence_by_physical_copy: dict[str, Fact]
    enabled_by_physical_copy: dict[str, Fact]
    restorable_by_physical_copy: dict[str, Fact]
    observations: tuple[Observation, ...]


def state_at(resource_id: str, system_id: str | None, category: str | None, audit_at: datetime, ledger: Ledger,
             last_delete_at: datetime | None, subject_user_id: str | None) -> ResourceState:
    observations = [o for o in ledger.by_resource.get(resource_id, []) if eligible(o, audit_at)]
    return ResourceState(
        resource_id,
        presence_by_physical_copy(resource_id, system_id, category, audit_at, ledger, last_delete_at,
                                  subject_user_id, observations),
        latest_fact_by_physical_copy(observations, observed_enabled, True) or _state_check(observations,
                                                                                         observed_enabled),
        latest_fact_by_physical_copy(observations, observed_restorable, True) or _state_check(observations,
                                                                                            observed_restorable),
        tuple(observations))


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
