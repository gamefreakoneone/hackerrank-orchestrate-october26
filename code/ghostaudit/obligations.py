"""Discovered resources + rules + state → Obligations (spec 0011, TECHNICAL_DESIGN §3.4)."""
from __future__ import annotations

from dataclasses import dataclass, field

from ghostaudit.identity import Subject
from ghostaudit.models import CurrentState, Obligation, RequiredState
from ghostaudit.timeline import Fact, ResourceState, exposed_direct_identifiers, has_user_link


@dataclass
class PolicyOutcome:
    obligations: list[Obligation] = field(default_factory=list)
    excluded: dict[str, str] = field(default_factory=dict)            # resource_id -> reason (no applicable rule)
    policy_undefined: list[str] = field(default_factory=list)          # condition FALSE: no rule-defined action
    condition_defaulted: list[str] = field(default_factory=list)       # condition UNKNOWN: default branch taken


def _proof(fact: Fact | None) -> tuple[str, str]:
    return (fact.proof, fact.proof_kind) if fact else ("", "")


def current_state(required: RequiredState, state: ResourceState, subject: Subject) -> tuple[CurrentState, Fact | None]:
    presence = state.presence
    if required in ("DISABLED", "BLOCKED"):
        fact = state.enabled if required == "DISABLED" else state.restorable
        if fact is not None:
            return ("ACTIVE" if fact.value else required), fact
        if presence is not None and presence.value == "absent":
            return "ABSENT", presence                 # the flow / archive no longer exists
        return "UNKNOWN", None
    if presence is None:
        return "UNKNOWN", None
    if presence.value == "absent":
        return "ABSENT", presence
    if required in ("REDACTED", "ANONYMIZED"):
        observation = presence.observation
        exposed = bool(exposed_direct_identifiers(observation, subject))
        if required == "ANONYMIZED" and has_user_link(observation, subject):
            exposed = True
        return ("EXPOSED" if exposed else required), presence
    return "PRESENT", presence


SATISFYING: dict[str, set[str]] = {
    "ABSENT": {"ABSENT"},
    "REDACTED": {"REDACTED", "ABSENT"},
    "ANONYMIZED": {"ANONYMIZED", "ABSENT"},
    "PRESENT": {"PRESENT"},
    "DISABLED": {"DISABLED", "ABSENT"},
    "BLOCKED": {"BLOCKED", "ABSENT"},
}


def build_obligation(*, system_id: str, resource_id: str, category: str, required: RequiredState, condition: str,
                     state: ResourceState, subject: Subject) -> Obligation:
    current, fact = current_state(required, state, subject)
    proof, proof_kind = _proof(fact)
    return Obligation(system_id=system_id, resource_id=resource_id, category=category, required=required,
                      current=current, condition=condition, proof=proof, proof_kind=proof_kind,
                      satisfied=current != "UNKNOWN" and current in SATISFYING[required])
