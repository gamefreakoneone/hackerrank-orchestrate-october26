import csv
import json
from pathlib import Path

import pytest

from ghostaudit.loaders import load_dataset
from ghostaudit.validate import validate_output

REPO_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_OUTPUT = REPO_ROOT / "dataset" / "sample_output.csv"   # format oracle (evaluation/tests only)


@pytest.fixture(scope="module")
def sample_dataset():
    return load_dataset(REPO_ROOT / "dataset", sample=True)


@pytest.fixture(scope="module")
def gold_rows():
    with SAMPLE_OUTPUT.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_rows(path, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["case_id", "deletion_status", "steps_json"])
        for row in rows:
            writer.writerow([row["case_id"], row["deletion_status"], row["steps_json"]])


def mutate(gold_rows, case_id, status=None, steps_fn=None):
    rows = []
    for row in gold_rows:
        row = dict(row)
        if row["case_id"] == case_id:
            steps = json.loads(row["steps_json"])
            if steps_fn:
                steps = steps_fn(steps)
            row["steps_json"] = json.dumps(steps)
            row["deletion_status"] = status or row["deletion_status"]
        rows.append(row)
    return rows


def first_incomplete(gold_rows):
    return next(r["case_id"] for r in gold_rows if r["deletion_status"] == "INCOMPLETE")


def run(tmp_path, dataset, rows, diagnostics=None):
    output = tmp_path / "out.csv"
    write_rows(output, rows)
    diagnostics_path = None
    if diagnostics is not None:
        diagnostics_path = tmp_path / "diagnostics.jsonl"
        diagnostics_path.write_text("".join(json.dumps(d) + "\n" for d in diagnostics))
    return validate_output(output, dataset, diagnostics_path)


def test_sample_output_validates_clean(tmp_path, sample_dataset, gold_rows):
    result = validate_output(SAMPLE_OUTPUT, sample_dataset)
    assert result.errors == [] and result.warnings == []


def test_swapped_order_fails(tmp_path, sample_dataset, gold_rows):
    case_id = first_incomplete(gold_rows)

    def swap(steps):
        steps[0], steps[-1] = steps[-1], steps[0]
        for number, step in enumerate(steps, 1):
            step["step_no"] = number
        return steps
    result = run(tmp_path, sample_dataset, mutate(gold_rows, case_id, steps_fn=swap))
    assert any("canonical order" in e for e in result.errors)


def test_wrong_state_fails(tmp_path, sample_dataset, gold_rows):
    case_id = first_incomplete(gold_rows)
    result = run(tmp_path, sample_dataset, mutate(
        gold_rows, case_id, steps_fn=lambda s: [{**s[0], "state": "ACTIVE"}, *s[1:]]))
    assert any("state ACTIVE does not match" in e for e in result.errors)


def test_wrong_phase_and_step_no_fail(tmp_path, sample_dataset, gold_rows):
    case_id = first_incomplete(gold_rows)
    result = run(tmp_path, sample_dataset, mutate(
        gold_rows, case_id, steps_fn=lambda s: [{**s[0], "phase": "VERIFICATION", "step_no": 5}, *s[1:]]))
    assert any("phase VERIFICATION does not match" in e for e in result.errors)
    assert any("not consecutive" in e for e in result.errors)


def test_late_file_citation_fails(tmp_path, sample_dataset, gold_rows):
    request = next(r for r in sample_dataset.requests if r.case_id == first_incomplete(gold_rows))
    late_file = next(f.file_id for f in sample_dataset.evidence.values() if f.captured_at > request.audit_at)
    result = run(tmp_path, sample_dataset, mutate(
        gold_rows, request.case_id, steps_fn=lambda s: [{**s[0], "evidence_id": late_file}, *s[1:]]))
    assert any("captured after audit_at" in e for e in result.errors)


def test_late_activity_citation_fails(tmp_path, sample_dataset, gold_rows):
    request = next(r for r in sample_dataset.requests if r.case_id == first_incomplete(gold_rows))
    late_check = next(a.activity_id for a in sample_dataset.activity
                      if a.event_type == "CHECK_DATA_FLOW" and a.event_time > request.audit_at)
    result = run(tmp_path, sample_dataset, mutate(
        gold_rows, request.case_id, steps_fn=lambda s: [{**s[0], "evidence_id": late_check}, *s[1:]]))
    assert any("after audit_at" in e for e in result.errors)


def test_operational_claim_citation_fails(tmp_path, sample_dataset, gold_rows):
    request = next(r for r in sample_dataset.requests if r.case_id == first_incomplete(gold_rows))
    delete_activity = next(a.activity_id for a in sample_dataset.activity
                           if a.event_type == "DELETE_RECORD" and a.event_time <= request.audit_at)
    result = run(tmp_path, sample_dataset, mutate(
        gold_rows, request.case_id, steps_fn=lambda s: [{**s[0], "evidence_id": delete_activity}, *s[1:]]))
    assert any("operational-claim activity" in e for e in result.errors)


def test_pre_cutoff_state_check_citation_passes(tmp_path, sample_dataset, gold_rows):
    request = next(r for r in sample_dataset.requests if r.case_id == first_incomplete(gold_rows))
    check = next(a.activity_id for a in sample_dataset.activity
                 if a.event_type == "CHECK_DATA_FLOW" and a.event_time <= request.audit_at)
    result = run(tmp_path, sample_dataset, mutate(
        gold_rows, request.case_id, steps_fn=lambda s: [{**s[0], "evidence_id": check}, *s[1:]]))
    assert result.errors == [] and result.activity_citations == 1


def test_duplicate_step_key_fails(tmp_path, sample_dataset, gold_rows):
    case_id = first_incomplete(gold_rows)

    def duplicate(steps):
        steps = [steps[0], dict(steps[0]), *steps[1:]]
        for number, step in enumerate(steps, 1):
            step["step_no"] = number
        return steps
    result = run(tmp_path, sample_dataset, mutate(gold_rows, case_id, steps_fn=duplicate))
    assert any("duplicate" in e for e in result.errors)


def test_incomplete_empty_requires_blocker_flag(tmp_path, sample_dataset, gold_rows):
    case_id = first_incomplete(gold_rows)
    rows = mutate(gold_rows, case_id, steps_fn=lambda s: [])
    assert any("requires NOT_APPLICABLE" in e for e in run(tmp_path, sample_dataset, rows).errors)
    with_flag = run(tmp_path, sample_dataset, rows, [{"case_id": case_id, "flags": ["EMPTY_OBLIGATIONS"]}])
    assert with_flag.errors == [] and len(with_flag.warnings) == 1


def test_missing_row_and_not_applicable_with_steps_fail(tmp_path, sample_dataset, gold_rows):
    rows = mutate(gold_rows, first_incomplete(gold_rows), status="NOT_APPLICABLE")[1:]
    errors = run(tmp_path, sample_dataset, rows).errors
    assert any("missing" in e for e in errors)
    assert any("NOT_APPLICABLE must have []" in e for e in errors)
