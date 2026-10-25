from pathlib import Path

import pytest

from ghostaudit.account_link import link_account
from ghostaudit.discovery import discover
from ghostaudit.evidence.index import build_ledger
from ghostaudit.identity import identifier_owner_index, resolve
from ghostaudit.loaders import load_dataset

DATASET_DIR = Path(__file__).resolve().parents[2] / "dataset"


@pytest.fixture(scope="module")
def world():
    dataset = load_dataset(DATASET_DIR, sample=True)
    return dataset, build_ledger(dataset)


def run(world, case_id):
    dataset, ledger = world
    request = next(r for r in dataset.requests if r.case_id == case_id)
    subject = resolve(request, dataset)
    found = discover(subject, request, dataset, ledger)
    link = link_account(subject, request, found, dataset, ledger, identifier_owner_index(dataset, request.audit_at))
    return request, subject, found, link


def test_case_06_decoy_name_does_not_link(world):
    _, subject, found, link = run(world, "case_06")
    assert {rid for rid, d in found.items() if d.grounded} == {"account_006", "search_001"}
    assert link.via == "grounded" and link.current == "account_006"


def test_case_15_trace_group_grounds_the_account(world):
    _, _, found, link = run(world, "case_15")
    assert link.current == "account_4745"
    assert any(l.via == "identifier" for l in found["account_4745"].links)


def test_case_17_multi_grounded_keeps_historical_account(world):
    _, _, _, link = run(world, "case_17")
    assert (link.via, link.current, link.historical) == ("multi_grounded", "account_4092", ["account_6523"])
    assert link.flags == ["ACCOUNT_MULTI_GROUNDED"]


def test_ungrounded_account_is_never_named(world):
    _, _, found, link = run(world, "case_01")
    assert link.via == "ungrounded" and link.current is None and link.flags == ["ACCOUNT_UNGROUNDED"]
    assert "account_001" in link.ranked_candidates            # diagnostics only
    assert "account_001" not in found


def test_post_cutoff_evidence_is_not_read(world):
    dataset, ledger = world
    request, subject, found, _ = run(world, "case_09")
    late = {o.resource_id for key in subject.key_values() for o in ledger.by_identifier.get(key, [])
            if o.captured_at > request.audit_at}
    assert "account_3960" in late                              # evidence_06 (captured after audit_at) names it
    assert "account_3960" not in found
