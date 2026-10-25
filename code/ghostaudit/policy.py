"""deletion_rules.csv → required end state and tri-state rule conditions (spec 0011, TECHNICAL_DESIGN §5 Q5)."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from ghostaudit.evidence.model import Observation
from ghostaudit.loaders import parse_ts
from ghostaudit.models import RequiredState, Rule

DATA_FLOW = "DATA_FLOW"
Condition = Literal["TRUE", "FALSE", "UNKNOWN"]
ACTION_REQUIRED: dict[str, RequiredState] = {"DELETE": "ABSENT", "REDACT": "REDACTED", "ANONYMIZE": "ANONYMIZED",
                                             "RETAIN": "PRESENT"}
RETENTION_FIELDS = {"SECURITY_AUDIT_LOG": ("retention_until",), "LEGAL_HOLD_RECORD": ("retained_until",)}
# REDACT / ANONYMIZE / RETAIN keep the record (AGENTS.md §6.4: "keep the record ..."); only DELETE removes it.
RECORD_PRESERVING_ACTIONS = frozenset({"REDACT", "ANONYMIZE", "RETAIN"})


def required_state(category: str, rule: Rule | None) -> RequiredState | None:
    if category == DATA_FLOW:
        return "DISABLED"                    # an active flow can recreate the data (AGENTS.md §6.5)
    if rule is None:
        return None
    if category == "BACKUP_ARCHIVE" and rule.required_action == "RETAIN":
        return "BLOCKED"                     # retained, with restore access blocked
    return ACTION_REQUIRED[rule.required_action]


def preservation_required(category: str, rule: Rule | None) -> bool:
    """A data flow is a process, not retained business data: its absence satisfies DISABLED."""
    return category != DATA_FLOW and rule is not None and rule.required_action in RECORD_PRESERVING_ACTIONS


def _latest_value(observations: list[Observation], field_names: tuple[str, ...]) -> str | None:
    for observation in sorted(observations, key=lambda o: (o.captured_at, o.evidence_id), reverse=True):
        for name in field_names:
            if observation.fields.get(name):
                return observation.fields[name]
    return None


def condition(category: str, rule: Rule | None, observations: list[Observation], audit_at: datetime) -> Condition:
    """TRUE ⇒ the rule's action; UNKNOWN (no field) ⇒ the rule's action, flagged; FALSE ⇒ no rule-defined action."""
    if category == DATA_FLOW or rule is None or rule.condition.strip().lower() == "always":
        return "TRUE"
    if category in RETENTION_FIELDS:
        value = _latest_value(observations, RETENTION_FIELDS[category])
        if value is None:
            return "UNKNOWN"
        try:
            return "TRUE" if parse_ts(value) >= audit_at else "FALSE"
        except ValueError:
            return "UNKNOWN"
    if category == "ACCOUNT_TOMBSTONE":
        status = _latest_value(observations, ("account_status",))
        return "TRUE" if status == "DELETED" else "UNKNOWN"
    return "UNKNOWN"


class CategoryChoice(BaseModel):
    record_kind: dict      # Jev choice answer: {"choice", "confidence", "probabilities"}


def category_fallback(llm, resource_id: str, system_id: str | None, rules: dict[str, Rule],
                      minimum_probability: float = 0.5) -> str | None:
    """Jev choice over the data categories, used only when no record field/table/event maps the resource."""
    from ghostaudit.llm.providers import LLMError
    criteria = {category: f"policy condition: {rule.condition}" for category, rule in sorted(rules.items())}
    criteria[DATA_FLOW] = "a connector or sync job that copies customer data to another system"
    try:
        answer = llm.call(task="category_fallback", schema=CategoryChoice, inputs={
            "state": {"record": {"resource_id": resource_id, "system": system_id or "unknown"}},
            "questions": {"record_kind": {"type": "choice", "criteria": criteria,
                                          "instructions": "Which kind of data record is `record`?"}}})
    except LLMError:
        return None
    choice = answer.record_kind.get("choice")
    probability = (answer.record_kind.get("probabilities") or {}).get(choice, 0.0)
    return choice if probability >= minimum_probability else None
