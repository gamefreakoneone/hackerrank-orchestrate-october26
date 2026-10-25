"""Vision revalidation on recorded Gemini responses (tests/fixtures/vision_*.json); no live calls."""
import json
from collections import Counter
from pathlib import Path

import pytest

from ghostaudit.evidence.vision import VisionExtraction, VisionRecord, identity_email_universe, revalidate
from ghostaudit.loaders import load_dataset

FIXTURES = Path(__file__).resolve().parent / "fixtures"
DATASET_DIR = Path(__file__).resolve().parents[2] / "dataset"


@pytest.fixture(scope="module")
def dataset():
    return load_dataset(DATASET_DIR)


@pytest.fixture(scope="module")
def universe(dataset):
    return identity_email_universe(dataset)


def recorded(file_id):
    return VisionExtraction.model_validate(json.loads((FIXTURES / f"vision_{file_id}.json").read_text()))


def run(dataset, universe, file_id, extraction):
    counts = Counter()
    evidence_file = dataset.evidence[file_id]
    return revalidate(file_id, evidence_file.captured_at, evidence_file.origin, extraction, universe, counts), counts


def test_connector_console_rows(dataset, universe):
    observations, _ = run(dataset, universe, "evidence_14", recorded("evidence_14"))
    by_id = {o.resource_id: o for o in observations}
    assert set(by_id) == {"data_flow_1121", "data_flow_9846"}
    assert by_id["data_flow_1121"].category == "DATA_FLOW" and by_id["data_flow_1121"].fields["enabled"] == "true"
    assert "jain.aditi@gmail.com" in by_id["data_flow_1121"].identifiers
    assert all(o.source_kind == "png" and o.evidence_id == "evidence_14" for o in observations)


def test_security_explorer_shows_only_user_03(dataset, universe):
    observations, _ = run(dataset, universe, "evidence_37", recorded("evidence_37"))
    assert {o.resource_id for o in observations} == {f"audit_record_00{n}" for n in range(1, 7)}
    assert all(o.identifiers == {"user_03"} and o.category == "SECURITY_AUDIT_LOG" for o in observations)


def test_unknown_emails_and_bad_ids_are_dropped(dataset, universe):
    observations, counts = run(dataset, universe, "evidence_32", recorded("evidence_32"))
    assert counts["dropped_identifier"] == 3                       # company emails outside the identity universe
    assert {i for o in observations for i in o.identifiers} == {"areed1433@gmail.com"}
    bad = VisionExtraction(records=[VisionRecord(resource_id="ORD-20263245", subject_identifiers=["user_17"])])
    observations, counts = run(dataset, universe, "evidence_42", bad)
    assert observations == [] and counts["dropped_resource_id"] == 1


def test_off_system_rows_get_no_screen_category(dataset, universe):
    extraction = VisionExtraction(records=[VisionRecord(resource_id="support_9538")])
    (observation,), _ = run(dataset, universe, "evidence_04", extraction)
    assert observation.system_id == "support_platform" and observation.category is None
