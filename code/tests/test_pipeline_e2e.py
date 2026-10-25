"""End-to-end (assessment + plan) on dev cases whose account link is grounded: the plan must equal the sample answer
exactly. The intent gate is tested in test_intent.py; here no model is called and the ledger has no PNG rows.
Reads sample_output.csv as a regression oracle (tests/evaluation only)."""
import csv
import json
from pathlib import Path

import pytest

from ghostaudit.evidence.index import build_ledger
from ghostaudit.loaders import load_dataset
from ghostaudit.pipeline import Context, assess
from ghostaudit.planner import plan
from ghostaudit.serialize import dumps_steps

DATASET_DIR = Path(__file__).resolve().parents[2] / "dataset"


@pytest.fixture(scope="module")
def context():
    dataset = load_dataset(DATASET_DIR, sample=True)
    return Context(dataset, build_ledger(dataset))


@pytest.fixture(scope="module")
def gold():
    with (DATASET_DIR / "sample_output.csv").open(encoding="utf-8", newline="") as handle:
        return {r["case_id"]: (r["deletion_status"], json.loads(r["steps_json"])) for r in csv.DictReader(handle)}


@pytest.mark.parametrize("case_id", ["case_05", "case_06", "case_11", "case_13", "case_19"])
def test_grounded_case_matches_gold(context, gold, case_id):
    request = next(r for r in context.dataset.requests if r.case_id == case_id)
    assessment = assess(request, context)
    status, steps = plan(assessment.policy.obligations, assessment.flags)
    assert status.value == gold[case_id][0]
    assert json.loads(dumps_steps(steps)) == gold[case_id][1]
    assert "ACCOUNT_UNGROUNDED" not in assessment.flags


def test_ungrounded_case_is_incomplete_without_account_steps(context):
    request = next(r for r in context.dataset.requests if r.case_id == "case_25")
    assessment = assess(request, context)
    status, steps = plan(assessment.policy.obligations, assessment.flags)
    assert status.value == "INCOMPLETE" and "ACCOUNT_UNGROUNDED" in assessment.flags
    assert not any(s.system_id == "account_service" for s in steps)
    assert assessment.account_link.ranked_candidates              # kept for diagnostics only
