"""Spec 0019 no-guess guards not covered by test_discovery.py: records without ownership information, same-file
co-occurrence and repeated requests with independent cutoffs never ground a resource."""
from pathlib import Path

import pytest

from ghostaudit.account_link import link_account
from ghostaudit.discovery import discover
from ghostaudit.evidence.index import build_ledger
from ghostaudit.identity import identifier_owner_index, resolve
from ghostaudit.loaders import load_dataset

DATASET_DIR = Path(__file__).resolve().parents[2] / "dataset"


@pytest.fixture(scope="module")
def evaluation_world():
    dataset = load_dataset(DATASET_DIR)               # evidence is global; requests are the evaluation set
    return dataset, build_ledger(dataset)


@pytest.fixture(scope="module")
def sample_world():
    dataset = load_dataset(DATASET_DIR, sample=True)
    return dataset, build_ledger(dataset)


def grounded(world, case_id):
    dataset, ledger = world
    request = next(r for r in dataset.requests if r.case_id == case_id)
    subject = resolve(request, dataset)
    found = discover(subject, request, dataset, ledger)
    link = link_account(subject, request, found, dataset, ledger, identifier_owner_index(dataset, request.audit_at))
    return request, {rid for rid, d in found.items() if d.grounded}, link


def test_null_profile_lookup_without_ownership_does_not_ground_an_account(sample_world):
    _, ledger = sample_world
    lookup = next(o for o in ledger.by_resource["account_3136"] if o.evidence_id == "evidence_92")
    assert lookup.fields.get("status_code") == "404" and not lookup.identifiers      # profile: null, no reference
    _, found, link = grounded(sample_world, "case_25")
    assert "account_3136" not in found and link.via == "ungrounded"
    assert "analytics_1895" not in found                                             # anonymized: all identifiers null


def test_same_file_co_occurrence_is_not_ownership(sample_world):
    _, ledger = sample_world
    subject_traces = [o for o in ledger.by_resource["account_7566"] if o.evidence_id == "evidence_94"]
    assert subject_traces and subject_traces[0].identifiers                          # the subject's readback trace
    anonymized = [o for o in ledger.by_resource["analytics_9406"] if o.evidence_id == "evidence_94"]
    assert anonymized and not anonymized[0].identifiers                              # same file, null lookup
    _, found, _ = grounded(sample_world, "case_03")
    assert "account_7566" in found and "analytics_9406" not in found


def test_repeated_requests_use_their_own_cutoffs(evaluation_world):
    earlier, earlier_found, _ = grounded(evaluation_world, "case_52")
    later, later_found, _ = grounded(evaluation_world, "case_33")
    assert earlier.audit_at < later.audit_at
    assert "export_1842" in later_found and "export_1842" not in earlier_found      # linked after case_52's cutoff
    assert "account_2373" not in later_found | earlier_found                         # linked only after both cutoffs
