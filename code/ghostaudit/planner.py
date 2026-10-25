"""Status decision and step plan (spec 0012, TECHNICAL_DESIGN §3.4–3.5). Code decides; citations are the proofs
that established each obligation's state (timeline: observed state → snapshot omission → state-check activity)."""
from __future__ import annotations

from ghostaudit.models import BLOCKER_FLAGS, OP_PHASE, OP_STATE, Obligation, Operation, Status, Step
from ghostaudit.obligations import treatment_violated
from ghostaudit.serialize import canonical

O = Operation
TEMPLATES: dict[str, tuple[Operation | None, Operation | None, Operation]] = {
    "ABSENT": (O.REPORT_REMAINING_RECORD, O.DELETE_RECORD, O.VERIFY_RECORD_ABSENT),
    "REDACTED": (O.REPORT_EXPOSED_PII, O.REDACT_RECORD, O.VERIFY_RECORD_REDACTED),
    "ANONYMIZED": (O.REPORT_EXPOSED_PII, O.ANONYMIZE_RECORD, O.VERIFY_RECORD_ANONYMIZED),
    "PRESENT": (None, None, O.VERIFY_RECORD_PRESENT),
    "BLOCKED": (O.REPORT_RESTORE_RISK, O.BLOCK_RESTORE, O.VERIFY_RESTORE_BLOCKED),
    "DISABLED": (O.REPORT_ACTIVE_DATA_FLOW, O.DISABLE_DATA_FLOW, O.VERIFY_DATA_FLOW_DISABLED),
}


def step(operation: Operation, obligation: Obligation, evidence_id: str) -> Step:
    return Step(step_no=0, phase=OP_PHASE[operation], system_id=obligation.system_id,
                resource_id=obligation.resource_id, operation=operation, state=OP_STATE[operation],
                evidence_id=evidence_id)


def decide_status(obligations: list[Obligation], flags: list[str]) -> Status:
    if set(flags) & BLOCKER_FLAGS or not obligations:
        return Status.INCOMPLETE
    return Status.COMPLETE if all(o.satisfied and o.proof for o in obligations) else Status.INCOMPLETE


def plan(obligations: list[Obligation], flags: list[str]) -> tuple[Status, list[Step]]:
    status = decide_status(obligations, flags)
    steps: list[Step] = []
    for obligation in obligations:
        finding, remediation, verification = TEMPLATES[obligation.required]
        if status == Status.COMPLETE:
            steps.append(step(verification, obligation, obligation.proof))
            continue
        if treatment_violated(obligation) and finding is not None:
            steps.append(step(finding, obligation, obligation.proof))
            steps.append(step(remediation, obligation, ""))
        steps.append(step(verification, obligation, ""))
    return status, canonical(steps)
