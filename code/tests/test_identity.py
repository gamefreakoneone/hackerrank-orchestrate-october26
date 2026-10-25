import dataclasses
from datetime import timedelta
from pathlib import Path

import pytest

from ghostaudit.identity import resolve, sha256_hex
from ghostaudit.loaders import load_dataset
from ghostaudit.models import AuditEvent

DATASET_DIR = Path(__file__).resolve().parents[2] / "dataset"


@pytest.fixture(scope="module")
def samples():
    return load_dataset(DATASET_DIR, sample=True)


def request_for(dataset, case_id):
    return next(r for r in dataset.requests if r.case_id == case_id)


def test_current_email_resolves_user_and_snapshot_values(samples):
    request = request_for(samples, "case_01")
    subject = resolve(request, samples)
    identity = samples.identities[subject.user_id]
    assert identity.email == request.email.strip().lower()
    assert subject.matches(identity.email.upper()) and subject.matches(identity.phone)
    assert subject.matches(identity.email_hash.upper()) and subject.matches(identity.name, kind="name")
    assert subject.matches(subject.user_id)


@pytest.mark.parametrize("case_id", ["case_10", "case_29"])
def test_historical_request_email(samples, case_id):
    request = request_for(samples, case_id)
    subject = resolve(request, samples)
    assert subject.user_id is not None
    assert request.email.strip().lower() in subject.historical_emails
    assert samples.identities[subject.user_id].email in subject.current_emails


def test_current_request_email_still_collects_historical_emails(samples):
    subject = resolve(request_for(samples, "case_12"), samples)     # request text mentions the old address
    assert subject.historical_emails and subject.current_emails


def test_hashes_recomputed_for_every_email(samples):
    subject = resolve(request_for(samples, "case_10"), samples)
    assert all(sha256_hex(email) in subject.email_hashes for email in subject.emails)


def test_post_cutoff_audit_row_is_ignored(samples):
    request = request_for(samples, "case_10")
    subject = resolve(request, samples)
    late_row = AuditEvent(audit_id="audit_late", user_id=subject.user_id,
                          event_time=request.audit_at + timedelta(seconds=1), field_name="email",
                          old_value=next(iter(subject.current_emails)), new_value="later.address@example.org")
    with_late_row = dataclasses.replace(samples, audit=[*samples.audit, late_row])
    assert resolve(request, with_late_row) == subject


def test_snapshot_after_cutoff_is_excluded(samples):
    request = request_for(samples, "case_10")
    subject = resolve(request, samples)
    identity = samples.identities[subject.user_id]
    late_identity = identity.model_copy(update={"updated_at": request.audit_at + timedelta(days=1)})
    late = dataclasses.replace(samples, identities={**samples.identities, identity.user_id: late_identity})
    late_subject = resolve(request, late)
    assert "IDENTITY_SNAPSHOT_AFTER_CUTOFF" in late_subject.flags
    assert late_subject.user_id == subject.user_id                   # found through a pre-cutoff audit email
    assert identity.name not in late_subject.names and not late_subject.current_emails


def test_decoy_names_never_substring_match(samples):
    subject = resolve(request_for(samples, "case_01"), samples)
    name = next(iter(subject.names))
    assert subject.matches(name, kind="name")
    assert not subject.matches(name + "lund", kind="name")
    assert not subject.matches(name.split()[0], kind="name")


def test_unknown_email_gives_email_only_subject(samples):
    request = request_for(samples, "case_01").model_copy(update={"email": "nobody@nowhere.example"})
    subject = resolve(request, samples)
    assert subject.user_id is None
    assert subject.emails == {"nobody@nowhere.example"}
    assert subject.email_hashes == {sha256_hex("nobody@nowhere.example")}
