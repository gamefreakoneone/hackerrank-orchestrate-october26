"""Spec 0017: state and treatment are reconstructed per physical copy before they are combined.
Small fictional ledgers; exercised through state_at → build_obligation → plan."""
from datetime import datetime, timezone

from ghostaudit.evidence.derive import make_observation
from ghostaudit.evidence.index import Ledger
from ghostaudit.evidence.model import SnapshotCoverage
from ghostaudit.identity import Subject
from ghostaudit.models import Operation, Status
from ghostaudit.obligations import build_obligation
from ghostaudit.planner import plan
from ghostaudit.timeline import state_at

AUDIT_AT = datetime(2026, 9, 30, tzinfo=timezone.utc)
EMAIL = "ada.quill@example.test"
SUBJECT = Subject(request_email=EMAIL, user_id="user_901", emails=frozenset({EMAIL}), phones=frozenset(),
                  names=frozenset({"Ada Quill"}), email_hashes=frozenset(), current_emails=frozenset({EMAIL}))
ACCOUNT, SUPPORT = "account_9001", "support_9002"


def day(number: int, hour: int = 12) -> datetime:
    return datetime(2026, 9, number, hour, tzinfo=timezone.utc) if number <= 30 else \
        datetime(2026, 10, number - 30, hour, tzinfo=timezone.utc)


def sql_row(evidence_id, captured_day, physical_copy, resource_id, container, **fields):
    return make_observation(evidence_id=evidence_id, captured_at=day(captured_day), source_kind="sql",
                            container=container, physical_copy=physical_copy, resource_id=resource_id,
                            fields={"resource_id": resource_id, **fields}, observed_at=day(captured_day, 11))


def service_read(evidence_id, captured_day, resource_id, physical_copy="export", observed_hour=12, **fields):
    return make_observation(evidence_id=evidence_id, captured_at=day(captured_day), source_kind="json",
                            container="profile_lookups", physical_copy=physical_copy, resource_id=resource_id,
                            fields={"resource_id": resource_id, **fields}, observed_at=day(captured_day, observed_hour))


def coverage(file_id, captured_day, physical_copy, collection="customer_profiles", system_id="account_service",
             resource_ids=()):
    return SnapshotCoverage(file_id=file_id, captured_at=day(captured_day), snapshot_at=day(captured_day, 11),
                            system_id=system_id, collection=collection, physical_copy=physical_copy,
                            scope="full_table", row_count=len(resource_ids), resource_ids=frozenset(resource_ids))


def ledger_of(observations, coverages=()):
    ledger = Ledger()
    ledger.add(list(observations), list(coverages))
    ledger.build_indexes()
    return ledger


def obligation(ledger, resource_id=ACCOUNT, system_id="account_service", category="USER_PROFILE", required="ABSENT"):
    state = state_at(resource_id, system_id, category, AUDIT_AT, ledger, None, SUBJECT.user_id)
    return build_obligation(system_id=system_id, resource_id=resource_id, category=category, required=required,
                            condition="TRUE", state=state, subject=SUBJECT,
                            preservation_required=required != "ABSENT")


REPLICA_HOLDS_ACCOUNT = sql_row("evidence_901", 10, "failover_replica", ACCOUNT, "customer_profiles", email=EMAIL)
REPLICA_COVERAGE = coverage("evidence_901", 10, "failover_replica", resource_ids=[ACCOUNT])
PRIMARY_404 = service_read("evidence_902", 20, ACCOUNT, status_code="404")


def test_primary_only_404_cannot_clear_a_replica_seen_present():
    result = obligation(ledger_of([REPLICA_HOLDS_ACCOUNT, PRIMARY_404], [REPLICA_COVERAGE]))
    assert (result.current, result.satisfied, result.proof) == ("PRESENT", False, "evidence_901")
    status, steps = plan([result], [])
    assert status == Status.INCOMPLETE
    finding = next(s for s in steps if s.operation == Operation.REPORT_REMAINING_RECORD)
    assert finding.evidence_id == "evidence_901"                     # the violating copy, not the newer 404
    copies = {c.physical_copy: (c.current, c.proof) for c in result.copy_states}
    assert copies == {"failover_replica": ("PRESENT", "evidence_901"), "primary": ("ABSENT", "evidence_902")}


def test_clean_primary_cannot_hide_replica_pii():
    replica = sql_row("evidence_911", 10, "read_replica", SUPPORT, "support_conversations", customer_email=EMAIL)
    clean_primary = service_read("evidence_912", 20, SUPPORT, customer_email=None, message_text="[redacted]")
    result = obligation(ledger_of([replica, clean_primary]), SUPPORT, "support_platform", "SUPPORT_MESSAGE",
                        "REDACTED")
    assert (result.current, result.satisfied, result.proof) == ("EXPOSED", False, "evidence_911")
    _, steps = plan([result], [])
    assert [s.evidence_id for s in steps if s.operation == Operation.REPORT_EXPOSED_PII] == ["evidence_911"]


def test_later_snapshot_of_the_same_replica_clears_it():
    later = [coverage("evidence_903", 25, "failover_replica"), coverage("evidence_903", 25, "primary")]
    result = obligation(ledger_of([REPLICA_HOLDS_ACCOUNT, PRIMARY_404], [REPLICA_COVERAGE, *later]))
    assert (result.current, result.satisfied) == ("ABSENT", True)
    copies = {c.physical_copy: (c.current, c.proof, c.rule) for c in result.copy_states}
    assert copies == {"failover_replica": ("ABSENT", "evidence_903", "snapshot_omission"),
                      "primary": ("ABSENT", "evidence_902", "observed")}
    status, steps = plan([result], [])
    assert status == Status.COMPLETE and steps[0].evidence_id == result.proof


def test_later_replica_pii_treatment_clears_it():
    replica = sql_row("evidence_911", 10, "read_replica", SUPPORT, "support_conversations", customer_email=EMAIL)
    replica_later = sql_row("evidence_913", 22, "read_replica", SUPPORT, "support_conversations",
                            customer_email=None)
    clean_primary = service_read("evidence_912", 20, SUPPORT, customer_email=None)
    result = obligation(ledger_of([replica, clean_primary, replica_later]), SUPPORT, "support_platform",
                        "SUPPORT_MESSAGE", "REDACTED")
    assert (result.current, result.satisfied, result.proof) == ("REDACTED", True, "evidence_913")


def test_later_observation_of_the_same_copy_supersedes_within_one_capture():
    present = service_read("evidence_921", 20, ACCOUNT, physical_copy="service_read", observed_hour=9,
                           status_code="200")
    gone = service_read("evidence_921", 20, ACCOUNT, physical_copy="service_read", observed_hour=10,
                        status_code="404")
    assert obligation(ledger_of([present, gone])).current == "ABSENT"
    assert obligation(ledger_of([gone.model_copy(update={"observed_at": day(20, 8)}), present])).current == "PRESENT"


def test_unrelated_copy_and_post_cutoff_snapshot_cannot_clear_the_target():
    unrelated = [coverage("evidence_904", 25, "reporting_replica"),
                 coverage("evidence_905", 25, "failover_replica", collection="customer_search_documents",
                          system_id="search_service")]
    post_cutoff = coverage("evidence_906", 32, "failover_replica")
    result = obligation(ledger_of([REPLICA_HOLDS_ACCOUNT, PRIMARY_404],
                                  [REPLICA_COVERAGE, *unrelated, post_cutoff]))
    assert (result.current, result.proof) == ("PRESENT", "evidence_901")


def test_format_label_is_not_all_replica_coverage():
    bundle = coverage("evidence_907", 25, "bundle")
    handover_absent = make_observation(evidence_id="evidence_908", captured_at=day(26), source_kind="txt",
                                       container="handover", physical_copy="service_read", resource_id=ACCOUNT,
                                       fields={"resource_id": ACCOUNT, "result": "NOT_FOUND"},
                                       observed_at=day(26, 9))
    result = obligation(ledger_of([REPLICA_HOLDS_ACCOUNT, PRIMARY_404, handover_absent],
                                  [REPLICA_COVERAGE, bundle]))
    assert (result.current, result.proof) == ("PRESENT", "evidence_901")


def test_newer_packaging_of_an_older_observation_does_not_overwrite_newer_state():
    gone = service_read("evidence_931", 20, ACCOUNT, status_code="404")                   # read on 09-20
    repackaged = service_read("evidence_932", 25, ACCOUNT, observed_hour=12, status_code="200")
    repackaged = repackaged.model_copy(update={"observed_at": day(15)})                   # 09-15 read, shipped 09-25
    result = obligation(ledger_of([gone, repackaged]))
    assert (result.current, result.proof) == ("ABSENT", "evidence_931")


def test_unestablished_state_stays_unknown():
    result = obligation(ledger_of([]))
    assert (result.current, result.satisfied, result.proof) == ("UNKNOWN", False, "")


def test_bundle_omission_clears_only_the_subjects_it_was_exported_for():
    present = service_read("evidence_941", 20, ACCOUNT, status_code="200")
    other_subjects = coverage("evidence_942", 25, "bundle").model_copy(update={"covered_subjects": frozenset({"user_7"})})
    assert obligation(ledger_of([present], [other_subjects])).current == "PRESENT"
    this_subject = other_subjects.model_copy(update={"covered_subjects": frozenset({"user_901"})})
    result = obligation(ledger_of([present], [this_subject]))
    assert (result.current, result.proof) == ("ABSENT", "evidence_942")
