"""Spec 0022: a fact influences a case only when it was both available (file captured) and observed by audit_at.
A record dated after its file's capture keeps its own time; it is never clipped back to the capture time."""
import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from ghostaudit.discovery import discover
from ghostaudit.evidence.derive import make_observation
from ghostaudit.evidence.index import Ledger, build_ledger, eligible
from ghostaudit.evidence.json_ import parse_json
from ghostaudit.evidence.logs import parse_log
from ghostaudit.evidence.model import SnapshotCoverage
from ghostaudit.identity import Subject
from ghostaudit.loaders import load_dataset
from ghostaudit.models import Request, Rule
from ghostaudit.pipeline import Context, assess
from ghostaudit.planner import plan
from ghostaudit.policy import condition
from ghostaudit.timeline import state_at

DATASET_DIR = Path(__file__).resolve().parents[2] / "dataset"
EMAIL = "ada.quill@example.test"
SUBJECT = Subject(request_email=EMAIL, user_id="user_901", emails=frozenset({EMAIL}), phones=frozenset(),
                  names=frozenset({"Ada Quill"}), email_hashes=frozenset(), current_emails=frozenset({EMAIL}))
ACCOUNT, SUPPORT = "account_9001", "support_9002"


def day(number: int, hour: int = 12) -> datetime:
    return datetime(2026, 9, number, hour, tzinfo=timezone.utc)


def lookup(evidence_id, captured_day, observed_day, result, resource_id=ACCOUNT, **fields):
    return make_observation(evidence_id=evidence_id, captured_at=day(captured_day), source_kind="json",
                            container="records", physical_copy="export", resource_id=resource_id,
                            fields={"resource_id": resource_id, "result": result, **fields},
                            observed_at=day(observed_day), system_id="account_service")


def ledger_of(observations, coverages=()):
    ledger = Ledger()
    ledger.add(list(observations), list(coverages))
    ledger.build_indexes()
    return ledger


def presence(ledger, audit_at, resource_id=ACCOUNT):
    state = state_at(resource_id, "account_service", "USER_PROFILE", audit_at, ledger, None, SUBJECT.user_id)
    return {copy: (fact.value, fact.proof) for copy, fact in state.presence_by_physical_copy.items()}


# --- participant-data regressions (review B1); IDs appear only here, never in runtime code ----------------------

@pytest.fixture(scope="module")
def full_context():
    dataset = load_dataset(DATASET_DIR)
    return Context(dataset, build_ledger(dataset, use_cache=False))


@pytest.mark.parametrize("case_id,account,evidence_id", [("case_135", "account_1417", "evidence_13"),
                                                         ("case_383", "account_5043", "evidence_36")])
def test_future_found_cannot_override_an_at_cutoff_not_found(full_context, case_id, account, evidence_id):
    request = next(r for r in full_context.dataset.requests if r.case_id == case_id)
    assessment = assess(request, full_context)
    obligation = next(o for o in assessment.policy.obligations if o.resource_id == account)
    assert (obligation.current, obligation.proof) == ("ABSENT", evidence_id)
    status, steps = plan(assessment.policy.obligations, assessment.flags)
    assert status.value == "COMPLETE" and all(s.phase.value == "VERIFICATION" for s in steps)


# --- fictional counterexamples ------------------------------------------------------------------------------------

def test_record_dated_after_its_capture_is_not_backdated():
    gone = lookup("evidence_901", 12, 12, "NOT_FOUND")
    found_later = lookup("evidence_901", 12, 14, "FOUND")              # same file, row dated two days later
    ledger = ledger_of([gone, found_later])
    assert not eligible(found_later, day(12)) and eligible(found_later, day(14))
    assert presence(ledger, day(12)) == {"primary": ("absent", "evidence_901")}
    assert presence(ledger, day(14)) == {"primary": ("present", "evidence_901")}   # both bounds passed


def test_future_only_identity_link_does_not_discover_the_record():
    future_link = lookup("evidence_902", 12, 14, "FOUND", resource_id=SUPPORT, customer_email=EMAIL)
    request = Request(case_id="case_x", email=EMAIL, requested_at=day(1), reported_status="COMPLETE",
                      reported_at=day(2), audit_at=day(12), request_text="Please delete my account.")
    no_activity = SimpleNamespace(activity=[])
    ledger = ledger_of([future_link])
    assert SUPPORT not in discover(SUBJECT, request, no_activity, ledger)
    later_request = request.model_copy(update={"audit_at": day(14)})
    assert SUPPORT in discover(SUBJECT, later_request, no_activity, ledger)


def test_mixed_time_trace_contributes_no_identifier_before_its_last_line():
    text = ("2026-09-10T12:00:00Z [INFO] [support_platform] [tr-mixed-1] message_read: resource_id=support_9002\n"
            f"2026-09-14T12:00:00Z [INFO] [support_platform] [tr-mixed-1] message_read: customer_email={EMAIL}\n")
    [observation] = parse_log("evidence_903", day(12), text)
    assert EMAIL in observation.identifiers and observation.observed_at == day(14)
    assert not eligible(observation, day(12))


def test_bundle_record_dated_after_its_snapshot_names_no_subject_and_manufactures_no_absence():
    bundle = {"snapshots": [{"data_store": "account_service", "collection": "customer_profiles",
                             "captured_at": "2026-09-12T12:00:00Z",
                             "records": [{"resource_id": "account_9003", "user_id": "user_700"},
                                         {"resource_id": ACCOUNT, "user_id": "user_901",
                                          "recorded_at": "2026-09-14T12:00:00Z"}]}]}
    observations, [coverage] = parse_json("evidence_904", day(12), json.dumps(bundle))
    assert coverage.covered_subjects == frozenset({"user_700"})
    assert ACCOUNT in coverage.resource_ids                         # the filtered row still is not an omission
    future_row = next(o for o in observations if o.resource_id == ACCOUNT)
    assert not eligible(future_row, day(12))
    assert presence(ledger_of(observations, [coverage]), day(12)) == {}   # unknown, not absent


def test_future_snapshot_cannot_prove_earlier_absence():
    present = lookup("evidence_905", 10, 10, "FOUND")
    future_snapshot = SnapshotCoverage(file_id="evidence_906", captured_at=day(11), snapshot_at=day(13),
                                       system_id="account_service", collection="customer_profiles",
                                       physical_copy="primary", scope="full_table", row_count=0,
                                       resource_ids=frozenset())
    ledger = ledger_of([present], [future_snapshot])
    assert presence(ledger, day(12)) == {"primary": ("present", "evidence_905")}
    assert presence(ledger, day(13)) == {"primary": ("absent", "evidence_906")}


def test_future_retention_date_is_business_metadata_not_a_future_observation():
    record = make_observation(evidence_id="evidence_907", captured_at=day(10), source_kind="json",
                              container="audit_records", physical_copy="export", resource_id="audit_record_9004",
                              fields={"resource_id": "audit_record_9004", "retention_until": "2027-09-01T00:00:00Z"},
                              observed_at=day(10), system_id="security_service")
    rule = Rule(rule_id="rule_x", data_category="SECURITY_AUDIT_LOG",
                condition="Record is within the supplied retention period", required_action="RETAIN")
    assert eligible(record, day(12))
    assert condition("SECURITY_AUDIT_LOG", rule, [record], day(12)) == "TRUE"
