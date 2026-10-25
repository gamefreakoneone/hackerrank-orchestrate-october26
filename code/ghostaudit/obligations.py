"""Discovered resources + rules + state → Obligations (specs 0011, 0017, 0018; TECHNICAL_DESIGN §3.4)."""
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


# Per-copy states that satisfy the required treatment. An absent copy exposes nothing and copies nothing; whether a
# kept record still exists is the separate preservation predicate (0018).
TREATMENT_SATISFIED_BY: dict[str, set[str]] = {
    "ABSENT": {"ABSENT"},
    "REDACTED": {"REDACTED", "ABSENT"},
    "ANONYMIZED": {"ANONYMIZED", "ABSENT"},
    "PRESENT": {"PRESENT", "ABSENT"},
    "DISABLED": {"DISABLED", "ABSENT"},
    "BLOCKED": {"BLOCKED", "ABSENT"},
}


def treatment_violated(obligation: Obligation) -> bool:
    """Something is present that must not be (record, identifiers, active flow, restore path): a reportable finding.
    A missing required record is never a finding — no operation can report or recreate it."""
    return obligation.current != "UNKNOWN" and obligation.current not in TREATMENT_SATISFIED_BY[obligation.required]


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
        states = {copy: ("ACTIVE" if fact.value else required, fact) for copy, fact in facts.items()}
        for copy, fact in presence.items():          # a later absence: the flow / archive no longer exists there
            if fact.value == "absent" and copy in states and fact.observed_at > states[copy][1].observed_at:
                states[copy] = ("ABSENT", fact)
        if not states and presence and all(fact.value == "absent" for fact in presence.values()):
            states = {copy: ("ABSENT", fact) for copy, fact in presence.items()}
        return states
    return {copy: (presence_current_state(required, fact, subject), fact) for copy, fact in presence.items()}


def record_is_preserved(category: str, state: ResourceState, subject: Subject) -> bool | None:
    """Some copy is present; a tombstone counts only while it keeps the subject's stable user_id. None = unknown."""
    facts = state.presence_by_physical_copy.values()
    if not facts:
        return None
    return any(fact.value == "present" and (category != "ACCOUNT_TOMBSTONE" or has_user_link(fact.observation, subject))
               for fact in facts)


def _latest(candidates):
    return max(candidates, key=lambda current_and_fact: (current_and_fact[1].observed_at, current_and_fact[1].proof))


def current_state(required: RequiredState, state: ResourceState, by_copy: dict[str, tuple[CurrentState, Fact]],
                  preservation_required: bool) -> tuple[CurrentState, Fact | None]:
    """A treatment violation in any copy wins and is the cited proof. A kept record that is absent in every copy is
    ABSENT (never relabelled as treated); otherwise a present compliant copy is cited. Nothing established ⇒ UNKNOWN."""
    if not by_copy:
        return "UNKNOWN", None
    violating = [cf for cf in by_copy.values() if cf[0] not in TREATMENT_SATISFIED_BY[required]]
    if violating:
        return _latest(violating)
    if not preservation_required:
        return _latest(by_copy.values())
    presence = state.presence_by_physical_copy
    if not presence:
        return "UNKNOWN", None
    if not any(fact.value == "present" for fact in presence.values()):
        return _latest(("ABSENT", fact) for fact in presence.values())
    return _latest([cf for cf in by_copy.values() if cf[0] != "ABSENT"] or by_copy.values())


def build_obligation(*, system_id: str, resource_id: str, category: str, required: RequiredState, condition: str,
                     state: ResourceState, subject: Subject, preservation_required: bool) -> Obligation:
    by_copy = current_state_by_physical_copy(required, state, subject)
    current, fact = current_state(required, state, by_copy, preservation_required)
    preserved = record_is_preserved(category, state, subject) if preservation_required else None
    copy_states = tuple(CopyState(physical_copy=copy, current=copy_current, proof=copy_fact.proof, rule=copy_fact.rule)
                        for copy, (copy_current, copy_fact) in sorted(by_copy.items()))
    satisfied = (current != "UNKNOWN" and current in TREATMENT_SATISFIED_BY[required]
                 and (not preservation_required or preserved is True))
    return Obligation(system_id=system_id, resource_id=resource_id, category=category, required=required,
                      current=current, condition=condition, proof=fact.proof if fact else "",
                      proof_kind=fact.proof_kind if fact else "", satisfied=satisfied, copy_states=copy_states,
                      preservation_required=preservation_required, required_record_is_preserved=preserved)
