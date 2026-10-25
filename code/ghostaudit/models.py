"""Key Contract models (TECHNICAL_DESIGN §3) and the operation tables."""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict


class Frozen(BaseModel):
    model_config = ConfigDict(frozen=True)


class Phase(StrEnum):
    FINDING = "FINDING"
    REMEDIATION = "REMEDIATION"
    VERIFICATION = "VERIFICATION"


class Status(StrEnum):
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class State(StrEnum):
    PRESENT = "PRESENT"
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    BLOCKED = "BLOCKED"
    ABSENT = "ABSENT"
    REDACTED = "REDACTED"
    ANONYMIZED = "ANONYMIZED"


class Operation(StrEnum):
    # declaration order == OP_ORDER (problem_statement.md operation table)
    REPORT_REMAINING_RECORD = "REPORT_REMAINING_RECORD"
    REPORT_EXPOSED_PII = "REPORT_EXPOSED_PII"
    REPORT_ACTIVE_DATA_FLOW = "REPORT_ACTIVE_DATA_FLOW"
    REPORT_RESTORE_RISK = "REPORT_RESTORE_RISK"
    DISABLE_DATA_FLOW = "DISABLE_DATA_FLOW"
    BLOCK_RESTORE = "BLOCK_RESTORE"
    DELETE_RECORD = "DELETE_RECORD"
    REDACT_RECORD = "REDACT_RECORD"
    ANONYMIZE_RECORD = "ANONYMIZE_RECORD"
    VERIFY_RECORD_ABSENT = "VERIFY_RECORD_ABSENT"
    VERIFY_RECORD_PRESENT = "VERIFY_RECORD_PRESENT"
    VERIFY_RECORD_REDACTED = "VERIFY_RECORD_REDACTED"
    VERIFY_RECORD_ANONYMIZED = "VERIFY_RECORD_ANONYMIZED"
    VERIFY_DATA_FLOW_DISABLED = "VERIFY_DATA_FLOW_DISABLED"
    VERIFY_RESTORE_BLOCKED = "VERIFY_RESTORE_BLOCKED"


O = Operation
OP_ORDER: dict[Operation, int] = {op: rank for rank, op in enumerate(Operation)}
OP_PHASE: dict[Operation, Phase] = {
    **{op: Phase.FINDING for op in (O.REPORT_REMAINING_RECORD, O.REPORT_EXPOSED_PII,
                                    O.REPORT_ACTIVE_DATA_FLOW, O.REPORT_RESTORE_RISK)},
    **{op: Phase.REMEDIATION for op in (O.DISABLE_DATA_FLOW, O.BLOCK_RESTORE, O.DELETE_RECORD,
                                        O.REDACT_RECORD, O.ANONYMIZE_RECORD)},
    **{op: Phase.VERIFICATION for op in (O.VERIFY_RECORD_ABSENT, O.VERIFY_RECORD_PRESENT, O.VERIFY_RECORD_REDACTED,
                                         O.VERIFY_RECORD_ANONYMIZED, O.VERIFY_DATA_FLOW_DISABLED,
                                         O.VERIFY_RESTORE_BLOCKED)},
}
OP_STATE: dict[Operation, State] = {
    O.REPORT_REMAINING_RECORD: State.PRESENT,
    O.REPORT_EXPOSED_PII: State.PRESENT,
    O.REPORT_ACTIVE_DATA_FLOW: State.ACTIVE,
    O.REPORT_RESTORE_RISK: State.ACTIVE,
    O.DISABLE_DATA_FLOW: State.DISABLED,
    O.BLOCK_RESTORE: State.BLOCKED,
    O.DELETE_RECORD: State.ABSENT,
    O.REDACT_RECORD: State.REDACTED,
    O.ANONYMIZE_RECORD: State.ANONYMIZED,
    O.VERIFY_RECORD_ABSENT: State.ABSENT,
    O.VERIFY_RECORD_PRESENT: State.PRESENT,
    O.VERIFY_RECORD_REDACTED: State.REDACTED,
    O.VERIFY_RECORD_ANONYMIZED: State.ANONYMIZED,
    O.VERIFY_DATA_FLOW_DISABLED: State.DISABLED,
    O.VERIFY_RESTORE_BLOCKED: State.BLOCKED,
}


class Step(Frozen):
    step_no: int
    phase: Phase
    system_id: str
    resource_id: str
    operation: Operation
    state: State
    evidence_id: str


class Request(Frozen):
    case_id: str
    email: str
    requested_at: datetime
    reported_status: str
    reported_at: datetime
    audit_at: datetime
    request_text: str


class Identity(Frozen):
    user_id: str
    name: str
    email: str
    phone: str
    email_hash: str
    updated_at: datetime


class AuditEvent(Frozen):
    audit_id: str
    user_id: str
    event_time: datetime
    field_name: str
    old_value: str
    new_value: str


class Activity(Frozen):
    activity_id: str
    event_time: datetime
    event_type: str
    source_system: str
    target_system: str
    resource_id: str
    reported_result: str
    details: str


class Rule(Frozen):
    rule_id: str
    data_category: str
    condition: str
    required_action: Literal["DELETE", "REDACT", "ANONYMIZE", "RETAIN"]


class EvidenceFile(Frozen):
    file_id: str
    file_path: str     # relative to dataset/
    origin: str
    captured_at: datetime


RequiredState = Literal["ABSENT", "REDACTED", "ANONYMIZED", "PRESENT", "DISABLED", "BLOCKED"]
CurrentState = Literal["PRESENT", "EXPOSED", "ACTIVE", "ABSENT", "REDACTED", "ANONYMIZED",
                       "DISABLED", "BLOCKED", "UNKNOWN"]


class CopyState(Frozen):
    """Diagnostics: the state one storage copy contributes to an obligation, and the evidence establishing it."""
    physical_copy: str
    current: CurrentState
    proof: str
    rule: str                         # observed | snapshot_omission | state_check_activity


class Obligation(Frozen):
    system_id: str
    resource_id: str
    category: str                     # data_category or "DATA_FLOW"
    required: RequiredState
    current: CurrentState
    condition: Literal["TRUE", "FALSE", "UNKNOWN"]
    proof: str
    proof_kind: Literal["file", "activity", "audit", ""]
    satisfied: bool
    copy_states: tuple[CopyState, ...] = ()   # every contributing copy; `proof` is the cited (violating) one
    preservation_required: bool = False       # the rule keeps the record (REDACT / ANONYMIZE / RETAIN)
    required_record_is_preserved: bool | None = None   # True: a copy is present (a tombstone with the subject's
                                              # user_id); False: absent in every established copy or the tombstone
                                              # lost its stable reference; None: unknown or not required


# Completion blockers (TECHNICAL_DESIGN §3.5): shared by the planner and the validator.
BLOCKER_FLAGS = frozenset({"ACCOUNT_UNGROUNDED", "UNKNOWN_STATE", "POLICY_UNDEFINED", "EMPTY_OBLIGATIONS",
                           "REQUIRED_RECORD_MISSING"})


def case_key(case_id: str) -> int:
    return int(case_id.rsplit("_", 1)[1])
