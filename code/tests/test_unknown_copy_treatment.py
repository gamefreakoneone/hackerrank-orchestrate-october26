"""Spec 0023: every copy where a flow or archive is known present takes part in DISABLED / BLOCKED. A copy with no
treatment fact is UNKNOWN (never dropped, never implied compliant); a known violation elsewhere is still reported."""
from datetime import datetime, timezone
from pathlib import Path

import pytest

from ghostaudit.evidence.derive import make_observation
from ghostaudit.evidence.index import Ledger, build_ledger
from ghostaudit.identity import Subject
from ghostaudit.loaders import load_dataset
from ghostaudit.models import Operation, Status
from ghostaudit.obligations import build_obligation
from ghostaudit.pipeline import Assessment, Context, assess
from ghostaudit.planner import plan
from ghostaudit.timeline import state_at

DATASET_DIR = Path(__file__).resolve().parents[2] / "dataset"
SUBJECT = Subject("audit-test@example.invalid", "user_99999", frozenset(), frozenset(), frozenset(), frozenset(),
                  frozenset())
AUDIT_AT = datetime(2026, 9, 1, tzinfo=timezone.utc)
FLOW = ("data_flow_99999", "integration_service", "DATA_FLOW", "DISABLED", "enabled", False)
BACKUP = ("backup_99999", "backup_service", "BACKUP_ARCHIVE", "BLOCKED", "restore_allowed", True)


def row(evidence_id, copy, resource, extra, hour=12, source_kind="sql"):
    resource_id, system_id, category = resource[:3]
    return make_observation(evidence_id=evidence_id, captured_at=AUDIT_AT.replace(hour=hour),
                            observed_at=AUDIT_AT.replace(hour=hour), source_kind=source_kind, container="fixture",
                            physical_copy=copy, resource_id=resource_id, system_id=system_id,
                            fields={"record_type": category, "user_id": SUBJECT.user_id, **extra})


def obligation(resource, observations, audit_at=AUDIT_AT.replace(hour=23)):
    resource_id, system_id, category, required, _, preserve = resource
    ledger = Ledger()
    ledger.add(observations, [])
    ledger.build_indexes()
    state = state_at(resource_id, system_id, category, audit_at, ledger, None, SUBJECT.user_id)
    return build_obligation(system_id=system_id, resource_id=resource_id, category=category, required=required,
                            condition="TRUE", state=state, subject=SUBJECT, preservation_required=preserve)


def copies(result):
    return {c.physical_copy: (c.current, c.proof, c.rule) for c in result.copy_states}


@pytest.mark.parametrize("resource", [FLOW, BACKUP], ids=["data_flow", "backup_archive"])
def test_present_copy_without_treatment_fact_is_unknown_not_dropped(resource):
    field_name, required = resource[4], resource[3]
    result = obligation(resource, [row("evidence_99998", "primary", resource, {field_name: "false"}),
                                   row("evidence_99999", "failover_replica", resource, {})])
    assert copies(result) == {"failover_replica": ("UNKNOWN", "evidence_99999", "presence_without_treatment"),
                              "primary": (required, "evidence_99998", "observed")}
    assert (result.current, result.satisfied, result.proof) == ("UNKNOWN", False, "")
    status, steps = plan([result], [])
    assert status == Status.INCOMPLETE
    assert [s.operation for s in steps] == [Operation.VERIFY_DATA_FLOW_DISABLED if required == "DISABLED"
                                            else Operation.VERIFY_RESTORE_BLOCKED]    # no invented finding


@pytest.mark.parametrize("resource", [FLOW, BACKUP], ids=["data_flow", "backup_archive"])
def test_later_treatment_fact_resolves_the_unknown_copy(resource):
    field_name, required = resource[4], resource[3]
    observations = [row("evidence_99998", "primary", resource, {field_name: "false"}),
                    row("evidence_99999", "failover_replica", resource, {}),
                    row("evidence_99997", "failover_replica", resource, {field_name: "false"}, hour=14)]
    result = obligation(resource, observations)
    assert (result.current, result.satisfied) == (required, True)
    assert plan([result], [])[0] == Status.COMPLETE
    before_resolution = obligation(resource, observations, audit_at=AUDIT_AT.replace(hour=13))   # post-cutoff fact
    assert (before_resolution.current, before_resolution.satisfied) == ("UNKNOWN", False)


def test_known_violation_is_reported_alongside_an_unknown_copy():
    result = obligation(FLOW, [row("evidence_99998", "primary", FLOW, {"enabled": "true"}),
                               row("evidence_99999", "failover_replica", FLOW, {})])
    assert (result.current, result.proof) == ("ACTIVE", "evidence_99998")
    assert copies(result)["failover_replica"][0] == "UNKNOWN"
    status, steps = plan([result], [])
    assert status == Status.INCOMPLETE
    assert [s.operation for s in steps] == [Operation.REPORT_ACTIVE_DATA_FLOW, Operation.DISABLE_DATA_FLOW,
                                            Operation.VERIFY_DATA_FLOW_DISABLED]


def test_absent_copy_settles_its_flow_but_a_retained_archive_absent_everywhere_is_missing():
    flow = obligation(FLOW, [row("evidence_99998", "primary", FLOW, {"enabled": "false"}),
                             row("evidence_99999", "failover_replica", FLOW, {"result": "NOT_FOUND"}, hour=13,
                                 source_kind="json")])
    assert {copy: state[0] for copy, state in copies(flow).items()} == {"failover_replica": "ABSENT",
                                                                         "primary": "DISABLED"}
    assert flow.satisfied
    backup_gone = obligation(BACKUP, [row("evidence_99996", "export", BACKUP, {"status_code": "404"},
                                          source_kind="json")])
    assert (backup_gone.current, backup_gone.satisfied, backup_gone.required_record_is_preserved) == \
        ("ABSENT", False, False)


def test_copy_level_uncertainty_is_a_completion_blocker_even_when_a_violation_is_reported():
    unknown_copy = obligation(FLOW, [row("evidence_99998", "primary", FLOW, {"enabled": "true"}),
                                     row("evidence_99999", "failover_replica", FLOW, {})])
    dataset = load_dataset(DATASET_DIR, sample=True)
    context = Context(dataset, build_ledger(dataset))
    grounded = assess(next(r for r in dataset.requests if r.case_id == "case_05"), context)
    assert "UNKNOWN_STATE" not in grounded.flags
    with_unknown_copy = Assessment(**{**grounded.__dict__,
                                      "policy": type(grounded.policy)(
                                          obligations=[*grounded.policy.obligations, unknown_copy])})
    assert "UNKNOWN_STATE" in with_unknown_copy.flags
