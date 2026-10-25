import builtins
from pathlib import Path

import pytest

from ghostaudit.loaders import load_dataset, parse_ts

DATASET_DIR = Path(__file__).resolve().parents[2] / "dataset"


@pytest.fixture(scope="module")
def dataset():
    return load_dataset(DATASET_DIR)


def test_row_counts(dataset):
    assert len(dataset.requests) == 518
    assert len(load_dataset(DATASET_DIR, sample=True).requests) == 32
    assert len(dataset.identities) == 850
    assert len(dataset.audit) == 306
    assert len(dataset.activity) == 4011
    assert len(dataset.rules) == 15
    assert len(dataset.evidence) == 94


def test_timestamps_are_aware_utc(dataset):
    request = dataset.requests[0]
    for value in (request.requested_at, request.reported_at, request.audit_at,
                  dataset.activity[0].event_time, dataset.audit[0].event_time,
                  next(iter(dataset.evidence.values())).captured_at):
        assert value.tzinfo is not None and value.utcoffset().total_seconds() == 0
    assert parse_ts("2026-01-01T00:00:00Z").isoformat() == "2026-01-01T00:00:00+00:00"
    with pytest.raises(ValueError):
        parse_ts("2026-01-01T00:00:00")


def test_sorted_orders(dataset):
    assert [a.event_time for a in dataset.activity] == sorted(a.event_time for a in dataset.activity)
    numbers = [int(r.case_id.split("_")[1]) for r in dataset.requests]
    assert numbers == sorted(numbers)


def test_loader_never_opens_sample_output(monkeypatch):
    real_open = Path.open

    def guarded_open(self, *args, **kwargs):
        assert self.name != "sample_output.csv"
        return real_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded_open)
    monkeypatch.setattr(builtins, "open", lambda *a, **k: pytest.fail("builtins.open used"))
    load_dataset(DATASET_DIR, sample=True)
