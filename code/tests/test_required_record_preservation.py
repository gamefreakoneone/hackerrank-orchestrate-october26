"""Spec 0018: a record the policy keeps (REDACT / ANONYMIZE / RETAIN) must be present and treated; absence never
satisfies it. Small fictional ledgers through state_at → build_obligation → Assessment.flags → plan → validator."""
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from ghostaudit.evidence.derive import make_observation
from ghostaudit.evidence.index import Ledger
from ghostaudit.evidence.model import SnapshotCoverage
from ghostaudit.identity import Subject
from ghostaudit.loaders import load_dataset
from ghostaudit.models import Operation, Rule, Status
from ghostaudit.obligations import PolicyOutcome, build_obligation
from ghostaudit.pipeline import Assessment
from ghostaudit.planner import plan
from ghostaudit.policy import preservation_required, required_state
from ghostaudit.serialize import dumps_steps
from ghostaudit.timeline import state_at
from ghostaudit.validate import validate_output

AUDIT_AT = datetime(2026, 9, 30, tzinfo=timezone.utc)
EMAIL = "ada.quill@example.test"
SUBJECT = Subject(request_email=EMAIL, user_id="user_901", emails=frozenset({EMAIL}), phones=frozenset(),
                  names=frozenset({"Ada Quill"}), email_hashes=frozenset(), current_emails=frozenset({EMAIL}))
RULES = {"ACCOUNT_TOMBSTONE": Rule(rule_id="r15", data_category="ACCOUNT_TOMBSTONE", condition="Account is deleted",
                                   required_action="REDACT"),
         "BACKUP_ARCHIVE": Rule(rule_id="r14", data_category="BACKUP_ARCHIVE",
                                condition="Restore access can be blocked", required_action="RETAIN"),
         "SUPPORT_MESSAGE": Rule(rule_id="r05", data_category="SUPPORT_MESSAGE", condition="Shared context",
                                 required_action="REDACT"),
         "USER_PROFILE": Rule(rule_id="r01", data_category="USER_PROFILE", condition="Always",
                              required_action="DELETE")}
RECORDS = {  # category -> (resource_id, system_id, collection)
    "ACCOUNT_TOMBSTONE": ("tombstone_9101", "identity_service", "deleted_customer_references"),
    "BACKUP_ARCHIVE": ("backup_9102", "backup_service", "backup_catalog"),
    "SUPPORT_MESSAGE": ("support_9103", "support_platform", "support_conversations"),
    "DATA_FLOW": ("data_flow_9104", "integration_service", "connector_configurations"),
    "USER_PROFILE": ("account_9105", "account_service", "customer_profiles"),
}


def day(number: int) -> datetime:
    return datetime(2026, 9, number, 12, tzinfo=timezone.utc)


def seen(category, evidence_id="evidence_951", captured_day=10, **fields):
    resource_id, system_id, collection = RECORDS[category]
    return make_observation(evidence_id=evidence_id, captured_at=day(captured_day), source_kind="sql",
                            container=collection, physical_copy="primary", resource_id=resource_id,
                            fields={"resource_id": resource_id, **fields}, system_id=system_id)


def omitted_later(category, file_id="evidence_952", captured_day=20):
    _, system_id, collection = RECORDS[category]
    return SnapshotCoverage(file_id=file_id, captured_at=day(captured_day), snapshot_at=day(captured_day),
                            system_id=system_id, collection=collection, physical_copy="primary", scope="full_table",
                            row_count=0, resource_ids=frozenset())


def obligation(category, observations=(), coverages=()):
    resource_id, system_id, _ = RECORDS[category]
    ledger = Ledger()
    ledger.add(list(observations), list(coverages))
    ledger.build_indexes()
    rule = RULES.get(category)
    state = state_at(resource_id, system_id, category, AUDIT_AT, ledger, None, SUBJECT.user_id)
    return build_obligation(system_id=system_id, resource_id=resource_id, category=category,
                            required=required_state(category, rule), condition="TRUE", state=state, subject=SUBJECT,
                            preservation_required=preservation_required(category, rule))


def planned(*obligations):
    assessment = Assessment(request=None, subject=SUBJECT, discovered={}, account_link=SimpleNamespace(flags=[]),
                            policy=PolicyOutcome(obligations=list(obligations)), categories={}, category_sources={})
    status, steps = plan(list(obligations), assessment.flags)
    return status, steps, assessment.flags


def operations(steps):
    return [(s.operation, s.evidence_id) for s in steps]


TOMBSTONE_CLEAN = dict(subject_reference="user_901", full_name=None, email=None, account_status="DELETED")
BACKUP_BLOCKED = dict(customer_reference="user_901", restore_allowed="false")


@pytest.mark.parametrize("category,present_fields,verification", [
    ("ACCOUNT_TOMBSTONE", TOMBSTONE_CLEAN, Operation.VERIFY_RECORD_REDACTED),
    ("BACKUP_ARCHIVE", BACKUP_BLOCKED, Operation.VERIFY_RESTORE_BLOCKED),
    ("SUPPORT_MESSAGE", dict(customer_reference="user_901", requester_email=None), Operation.VERIFY_RECORD_REDACTED),
])
def test_missing_required_record_blocks_completion(category, present_fields, verification):
    result = obligation(category, [seen(category, **present_fields)], [omitted_later(category)])
    assert (result.preservation_required, result.required_record_is_preserved) == (True, False)
    assert (result.current, result.satisfied, result.proof) == ("ABSENT", False, "evidence_952")
    status, steps, flags = planned(result)
    assert status == Status.INCOMPLETE and "REQUIRED_RECORD_MISSING" in flags
    # no finding or remediation is invented (the schema cannot recreate a record); the future check stays
    assert operations(steps) == [(verification, "")]


def test_unknown_presence_is_not_proven_absence():
    result = obligation("ACCOUNT_TOMBSTONE")
    assert (result.current, result.required_record_is_preserved) == ("UNKNOWN", None)
    _, _, flags = planned(result)
    assert "UNKNOWN_STATE" in flags and "REQUIRED_RECORD_MISSING" not in flags


def test_redacted_tombstone_with_stable_reference_passes():
    result = obligation("ACCOUNT_TOMBSTONE", [seen("ACCOUNT_TOMBSTONE", **TOMBSTONE_CLEAN)])
    assert (result.current, result.satisfied, result.required_record_is_preserved) == ("REDACTED", True, True)
    status, steps, _ = planned(result)
    assert status == Status.COMPLETE and operations(steps) == [(Operation.VERIFY_RECORD_REDACTED, "evidence_951")]


def test_tombstone_without_stable_reference_does_not_pass():
    without_reference = dict(TOMBSTONE_CLEAN, subject_reference=None)
    result = obligation("ACCOUNT_TOMBSTONE", [seen("ACCOUNT_TOMBSTONE", **without_reference)])
    assert (result.satisfied, result.required_record_is_preserved) == (False, False)
    status, steps, flags = planned(result)
    assert status == Status.INCOMPLETE and "REQUIRED_RECORD_MISSING" in flags
    assert operations(steps) == [(Operation.VERIFY_RECORD_REDACTED, "")]


def test_tombstone_still_exposing_pii_is_reported():
    leaked = dict(TOMBSTONE_CLEAN, email=EMAIL)
    result = obligation("ACCOUNT_TOMBSTONE", [seen("ACCOUNT_TOMBSTONE", **leaked)])
    assert (result.current, result.satisfied, result.required_record_is_preserved) == ("EXPOSED", False, True)
    _, steps, _ = planned(result)
    assert operations(steps) == [(Operation.REPORT_EXPOSED_PII, "evidence_951"), (Operation.REDACT_RECORD, ""),
                                 (Operation.VERIFY_RECORD_REDACTED, "")]


def test_retained_backup_blocked_passes_and_restorable_is_a_risk():
    blocked = obligation("BACKUP_ARCHIVE", [seen("BACKUP_ARCHIVE", **BACKUP_BLOCKED)])
    assert (blocked.current, blocked.satisfied) == ("BLOCKED", True)
    restorable = obligation("BACKUP_ARCHIVE", [seen("BACKUP_ARCHIVE", **dict(BACKUP_BLOCKED, restore_allowed="true"))])
    assert (restorable.current, restorable.satisfied) == ("ACTIVE", False)
    _, steps, _ = planned(restorable)
    assert operations(steps)[:2] == [(Operation.REPORT_RESTORE_RISK, "evidence_951"), (Operation.BLOCK_RESTORE, "")]


def test_preserve_and_treat_record_is_never_planned_as_delete():
    result = obligation("SUPPORT_MESSAGE", [seen("SUPPORT_MESSAGE", requester_email=EMAIL)])
    assert (result.required, result.current) == ("REDACTED", "EXPOSED")
    _, steps, _ = planned(result)
    assert Operation.DELETE_RECORD not in {s.operation for s in steps}


def test_absence_still_satisfies_delete_and_a_removed_data_flow():
    profile = obligation("USER_PROFILE", [seen("USER_PROFILE", email=EMAIL)], [omitted_later("USER_PROFILE")])
    assert (profile.preservation_required, profile.current, profile.satisfied) == (False, "ABSENT", True)
    flow = obligation("DATA_FLOW", [seen("DATA_FLOW", enabled="true")], [omitted_later("DATA_FLOW")])
    assert (flow.preservation_required, flow.current, flow.satisfied) == (False, "ABSENT", True)


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_validator_accepts_the_blocked_plan_only_with_the_shared_blocker(tmp_path):
    result = obligation("ACCOUNT_TOMBSTONE", [seen("ACCOUNT_TOMBSTONE", **TOMBSTONE_CLEAN)],
                        [omitted_later("ACCOUNT_TOMBSTONE")])
    status, steps, flags = planned(result)
    dataset = load_dataset(REPO_ROOT / "dataset", sample=True)
    with (REPO_ROOT / "dataset" / "sample_output.csv").open(encoding="utf-8", newline="") as handle:
        rows = [dict(row) for row in csv.DictReader(handle)]
    rows[0].update(deletion_status=status.value, steps_json=dumps_steps(steps))
    output = tmp_path / "out.csv"
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, ["case_id", "deletion_status", "steps_json"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    def validate(case_flags):
        diagnostics = tmp_path / "diagnostics.jsonl"
        diagnostics.write_text(json.dumps({"case_id": rows[0]["case_id"], "flags": case_flags}) + "\n")
        return validate_output(output, dataset, diagnostics)

    with_blocker = validate(flags)
    assert with_blocker.ok and any("REQUIRED_RECORD_MISSING" in w for w in with_blocker.warnings)
    assert not validate([]).ok
