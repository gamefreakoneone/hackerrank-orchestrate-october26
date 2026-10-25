"""Metamorphic tests: transformations that must leave outputs unchanged, or change them only as expected."""
import csv
import dataclasses
import random
import shutil
from datetime import timedelta
from pathlib import Path

import pytest

from ghostaudit.evidence.index import build_ledger
from ghostaudit.loaders import load_dataset
from ghostaudit.models import AuditEvent
from ghostaudit.pipeline import Context, assess
from ghostaudit.planner import plan
from ghostaudit.serialize import dumps_steps

DATASET_DIR = Path(__file__).resolve().parents[2] / "dataset"


def outputs(dataset, case_ids=None) -> dict[str, tuple[str, str]]:
    ctx = Context(dataset, build_ledger(dataset, use_cache=False))
    result = {}
    for request in dataset.requests:
        if case_ids is None or request.case_id in case_ids:
            assessment = assess(request, ctx)
            status, steps = plan(assessment.policy.obligations, assessment.flags)
            result[request.case_id] = (status.value, dumps_steps(steps))
    return result


@pytest.fixture(scope="module")
def samples():
    return load_dataset(DATASET_DIR, sample=True)


@pytest.fixture(scope="module")
def baseline(samples):
    return outputs(samples)


def test_post_cutoff_audit_row_leaves_output_unchanged(samples, baseline):
    extra = []
    for request in samples.requests:
        user_id = next((i.user_id for i in samples.identities.values()
                        if i.email == request.email.strip().lower()), None)
        if user_id:
            extra.append(AuditEvent(audit_id=f"audit_late_{request.case_id}", user_id=user_id,
                                    event_time=request.audit_at + timedelta(hours=1), field_name="email",
                                    old_value=request.email.strip().lower(), new_value=f"late.{user_id}@example.net"))
    changed = dataclasses.replace(samples, audit=sorted([*samples.audit, *extra],
                                                        key=lambda a: (a.event_time, a.audit_id)))
    assert extra and outputs(changed) == baseline


def copy_dataset(tmp_path: Path) -> Path:
    target = tmp_path / "dataset"
    shutil.copytree(DATASET_DIR, target)
    return target


def test_shuffled_csv_rows_leave_output_unchanged(tmp_path, baseline):
    target = copy_dataset(tmp_path)
    rng = random.Random(7)
    for name in ("user_identities.csv", "user_audit_log.csv", "system_activity.csv", "evidence_files.csv",
                 "deletion_rules.csv", "sample_deletion_requests.csv"):
        with (target / name).open(encoding="utf-8", newline="") as handle:
            header, *rows = list(csv.reader(handle))
        rng.shuffle(rows)
        with (target / name).open("w", encoding="utf-8", newline="") as handle:
            csv.writer(handle, lineterminator="\n").writerows([header, *rows])
    assert outputs(load_dataset(target, sample=True)) == baseline


def test_unrelated_user_records_leave_output_unchanged(tmp_path, baseline):
    target = copy_dataset(tmp_path)
    with (target / "user_identities.csv").open("a", encoding="utf-8", newline="") as handle:
        csv.writer(handle, lineterminator="\n").writerow(
            ["user_9999", "Noor Unrelated", "noor.unrelated@example.net", "+31 6 9999 0000", "0" * 64,
             "2026-01-01T00:00:00Z"])
    (target / "evidence" / "logs" / "unrelated_9999.log").write_text(
        "2026-09-01T08:00:00Z level=DEBUG service=account_service trace_id=rb-999999-001 event=profile_lookup_started "
        "resource_id=account_99999 lookup_key=noor.unrelated@example.net\n"
        "2026-09-01T08:00:00Z level=INFO service=account_service trace_id=rb-999999-001 event=profile_lookup_completed "
        "resource_id=account_99999 rows=1 http_status=200\n", encoding="utf-8")
    with (target / "evidence_files.csv").open("a", encoding="utf-8", newline="") as handle:
        csv.writer(handle, lineterminator="\n").writerow(
            ["evidence_9999", "evidence/logs/unrelated_9999.log", "service_readback_logs", "2026-09-01T09:00:00Z"])
    assert outputs(load_dataset(target, sample=True)) == baseline


def evidence_used(dataset) -> dict[str, set[str]]:
    """Per case: files used as obligation proofs, discovery links, or eligible snapshot-omission candidates."""
    ctx = Context(dataset, build_ledger(dataset, use_cache=False))
    used = {}
    for request in dataset.requests:
        assessment = assess(request, ctx)
        systems = {o.system_id for o in assessment.policy.obligations}
        used[request.case_id] = {o.proof for o in assessment.policy.obligations} | {
            link.evidence_id for d in assessment.discovered.values() for link in d.links} | {
            c.file_id for system in systems for c in ctx.ledger.coverage_by_system.get(system, [])
            if c.captured_at <= request.audit_at}
    return used


def test_moving_a_file_past_the_cutoff_removes_it_and_only_changes_dependent_cases(tmp_path, samples, baseline):
    target = copy_dataset(tmp_path)
    with (target / "evidence_files.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    rows = [row if row[0] != "evidence_54" else [*row[:3], "2026-12-31T00:00:00Z"] for row in rows]
    with (target / "evidence_files.csv").open("w", encoding="utf-8", newline="") as handle:
        csv.writer(handle, lineterminator="\n").writerows(rows)
    moved = outputs(load_dataset(target, sample=True))
    assert all("evidence_54" not in steps for _, steps in moved.values())
    dependent = {case for case, files in evidence_used(samples).items() if "evidence_54" in files}
    changed = {case for case in baseline if moved[case] != baseline[case]}
    assert changed and changed <= dependent
