from datetime import datetime, timezone

import pytest

from ghostaudit.evidence.model import Observation
from ghostaudit.identity import Subject
from ghostaudit.obligations import build_obligation
from ghostaudit.timeline import Fact, ResourceState

T = datetime(2026, 9, 1, tzinfo=timezone.utc)
SUBJECT = Subject(request_email="a@x.com", user_id="user_9", emails=frozenset({"a@x.com"}), phones=frozenset(),
                  names=frozenset({"Ada Lovelace"}), email_hashes=frozenset(), current_emails=frozenset({"a@x.com"}))


def obs(identifiers=(), **fields):
    return Observation(evidence_id="evidence_7", captured_at=T, observed_at=None, source_kind="json", container="c",
                       physical_copy="export", system_id="s", resource_id="r_1", category=None,
                       identifiers=frozenset(identifiers), fields=fields)


def state(presence=None, enabled=None, restorable=None):
    def by_copy(value, observation=None):
        return {} if value is None else {"primary": Fact(value, "evidence_7", "file", observation, "observed",
                                                         "primary", T)}
    return ResourceState("r_1", by_copy(*presence) if presence else {}, by_copy(enabled), by_copy(restorable), ())


def oblige(required, resource_state):
    return build_obligation(system_id="s", resource_id="r_1", category="C", required=required, condition="TRUE",
                            state=resource_state, subject=SUBJECT,
                            preservation_required=required in ("REDACTED", "ANONYMIZED", "PRESENT", "BLOCKED"))


@pytest.mark.parametrize("required,resource_state,current,satisfied", [
    ("ABSENT", state(("present", obs())), "PRESENT", False),
    ("ABSENT", state(("absent", None)), "ABSENT", True),
    ("REDACTED", state(("present", obs(["a@x.com"]))), "EXPOSED", False),
    ("REDACTED", state(("present", obs(["user_9"]))), "REDACTED", True),                  # user_id may remain
    ("REDACTED", state(("present", obs(message_text="Hi, Ada Lovelace here"))), "EXPOSED", False),
    ("ANONYMIZED", state(("present", obs(["user_9"]))), "EXPOSED", False),                # link still present
    ("ANONYMIZED", state(("present", obs())), "ANONYMIZED", True),
    ("PRESENT", state(("present", obs())), "PRESENT", True),
    ("PRESENT", state(("absent", None)), "ABSENT", False),
    ("DISABLED", state(enabled=True), "ACTIVE", False),
    ("DISABLED", state(enabled=False), "DISABLED", True),
    ("BLOCKED", state(("present", obs()), restorable=True), "ACTIVE", False),
    ("BLOCKED", state(("present", obs()), restorable=False), "BLOCKED", True),
    ("BLOCKED", state(restorable=False), "UNKNOWN", False),                  # retained backup presence unknown
    ("ABSENT", state(), "UNKNOWN", False),
])
def test_templates(required, resource_state, current, satisfied):
    obligation = oblige(required, resource_state)
    assert (obligation.current, obligation.satisfied) == (current, satisfied)
    assert obligation.proof == ("" if current == "UNKNOWN" else "evidence_7")


def test_tombstone_keeps_user_id_but_not_name():
    clean = oblige("REDACTED", state(("present", obs(["user_9"], subject_reference="user_9", name=None))))
    leaked = oblige("REDACTED", state(("present", obs(["user_9", "Ada Lovelace"], name="Ada Lovelace"))))
    assert clean.satisfied and not leaked.satisfied
