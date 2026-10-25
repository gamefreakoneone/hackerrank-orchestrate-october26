"""Discovered resources + rules + state → Obligations (specs 0011, 0017; TECHNICAL_DESIGN §3.4)."""
from __future__ import annotations

from dataclasses import dataclass, field

from ghostaudit.identity import Subject
from ghostaudit.models import CopyState, CurrentState, Obligation, RequiredState
from ghostaudit.timeline import Fact, ResourceState, exposed_direct_identifiers, has_user_link


@dataclass
class PolicyOutcome:
    obligations: list[Obligation] = field(default_factory=list)
    excluded: dict[str, str] = field(default_factory=dict)            # resource_id -> reason (no applicable rule)
    policy_undefined: list[str] = field(default_factory=list)          # condition FALSE: no rule-defined action
    condition_defaulted: list[str] = field(default_factory=list)       # condition UNKNOWN: default branch taken


SATISFYING: dict[str, set[str]] = {
    "ABSENT": {"ABSENT"},
    "REDACTED": {"REDACTED", "ABSENT"},
    "ANONYMIZED": {"ANONYMIZED", "ABSENT"},
    "PRESENT": {"PRESENT"},
    "DISABLED": {"DISABLED", "ABSENT"},
    "BLOCKED": {"BLOCKED", "ABSENT"},
}


def presence_current_state(required: RequiredState, fact: Fact, subject: Subject) -> CurrentState:
    if fact.value == "absent":
        return "ABSENT"
    if required in ("REDACTED", "ANONYMIZED"):
        exposed = bool(exposed_direct_identifiers(fact.observation, subject))
        if required == "ANONYMIZED" and has_user_link(fact.observation, subject):
            exposed = True
        return "EXPOSED" if exposed else required
    return "PRESENT"


def current_state_by_physical_copy(required: RequiredState, state: ResourceState,
                                   subject: Subject) -> dict[str, tuple[CurrentState, Fact]]:
    presence = state.presence_by_physical_copy
    if required in ("DISABLED", "BLOCKED"):
        facts = state.enabled_by_physical_copy if required == "DISABLED" else state.restorable_by_physical_copy
        if facts:
            return {copy: ("ACTIVE" if fact.value else required, fact) for copy, fact in facts.items()}
        if presence and all(fact.value == "absent" for fact in presence.values()):
            return {copy: ("ABSENT", fact) for copy, fact in presence.items()}   # the flow / archive no longer exists
        return {}
    return {copy: (presence_current_state(required, fact, subject), fact) for copy, fact in presence.items()}


def current_state(required: RequiredState, state: ResourceState,
                  subject: Subject) -> tuple[CurrentState, Fact | None, tuple[CopyState, ...]]:
    """An outstanding violation in any copy wins over clean copies and is the cited proof; otherwise the latest
    compliant copy is cited. No established copy ⇒ UNKNOWN."""
    by_copy = current_state_by_physical_copy(required, state, subject)
    copy_states = tuple(CopyState(physical_copy=copy, current=current, proof=fact.proof, rule=fact.rule)
                        for copy, (current, fact) in sorted(by_copy.items()))
    if not by_copy:
        return "UNKNOWN", None, ()
    violating = [(current, fact) for current, fact in by_copy.values() if current not in SATISFYING[required]]
    current, fact = max(violating or by_copy.values(), key=lambda cf: (cf[1].observed_at, cf[1].proof))
    return current, fact, copy_states


def build_obligation(*, system_id: str, resource_id: str, category: str, required: RequiredState, condition: str,
                     state: ResourceState, subject: Subject) -> Obligation:
    current, fact, copy_states = current_state(required, state, subject)
    return Obligation(system_id=system_id, resource_id=resource_id, category=category, required=required,
                      current=current, condition=condition, proof=fact.proof if fact else "",
                      proof_kind=fact.proof_kind if fact else "",
                      satisfied=current != "UNKNOWN" and current in SATISFYING[required], copy_states=copy_states)
