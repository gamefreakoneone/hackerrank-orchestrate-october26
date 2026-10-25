from pathlib import Path

import pytest

from ghostaudit.evidence.index import build_ledger
from ghostaudit.loaders import load_dataset
from ghostaudit.timeline import delete_claim_times, last_delete_before, resource_category, state_at

DATASET_DIR = Path(__file__).resolve().parents[2] / "dataset"


@pytest.fixture(scope="module")
def world():
    dataset = load_dataset(DATASET_DIR, sample=True)
    return dataset, build_ledger(dataset), delete_claim_times(dataset.activity)


def state(world, case_id, resource_id, system_id):
    dataset, ledger, deletes = world
    audit_at = next(r for r in dataset.requests if r.case_id == case_id).audit_at
    return state_at(resource_id, system_id, resource_category(resource_id, audit_at, ledger), audit_at, ledger,
                    last_delete_before(deletes, resource_id, audit_at))


def test_case_05_replica_drift_keeps_account_present(world):
    presence = state(world, "case_05", "account_005", "account_service").presence
    assert (presence.value, presence.proof, presence.observation.physical_copy) == \
        ("present", "evidence_54", "failover_replica")


def test_case_01_full_table_omission_proves_absence(world):
    presence = state(world, "case_01", "account_001", "account_service").presence
    assert (presence.value, presence.proof, presence.rule) == ("absent", "evidence_54", "snapshot_omission")


def test_case_31_empty_bundle_collection_proves_absence(world):
    presence = state(world, "case_31", "account_4857", "account_service").presence
    assert (presence.value, presence.proof) == ("absent", "evidence_51")


def test_case_17_backup_is_restorable(world):
    restorable = state(world, "case_17", "backup_3245", "backup_service").restorable
    assert restorable is not None and restorable.value is True and restorable.proof_kind == "file"


def test_cache_miss_inside_a_trace_is_not_absence(world):
    presence = state(world, "case_15", "audit_record_1596", "security_service").presence
    assert presence.value == "present" and presence.proof == "evidence_01"


def test_unreachable_resource_is_unknown(world):
    current = state(world, "case_09", "audit_record_4902", "security_service")
    assert current.presence is None
