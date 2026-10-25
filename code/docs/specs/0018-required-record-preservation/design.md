# Spec 0018 — Required record preservation: design

## Data and decisions

Use the per-copy evidence from 0017. Extend the existing internal Obligation only with preservation information
the planner/diagnostics need, such as `preservation_required`, `required_retained_record_is_present` and its proof.
Preserve the distinction between absent, unknown, present-but-exposed, and present-and-treated.

- Compute `satisfied` from both required presence and required treatment; do not accept `current="ABSENT"`
  through the global REDACTED/ANONYMIZED/BLOCKED shortcut when the policy requires the record to remain.
- A missing required record sets an internal `REQUIRED_RECORD_MISSING` blocker (planned), or an equally
  explicit shared name documented in the contract. Unknown presence uses UNKNOWN_STATE. Add the blocker once
  in a shared declaration used by the planner and validator: their current duplicate sets are a real DRY case.
- Preserve current-state facts in diagnostics. An absent retained record remains absent; do not relabel it
  REDACTED/BLOCKED merely to fit an output operation.
- For INCOMPLETE output, emit only supported findings/remediation. The schema has no general operation to
  recreate missing retained data: record the blocker and the absence of an expressible remediation instead of
  inventing one. Existing future verification operations can describe the required end state with empty evidence.
- For COMPLETE, the selected proof(s) must establish both preservation and treatment. Reuse the existing
  verification templates where their meaning covers the requirement; do not mechanically duplicate every
  step to mirror internal predicates. Preserve all supporting proof IDs in diagnostics.

Touch `policy.py`, `obligations.py`, internal models, `planner.py`, `validate.py` and their direct consumers only
as needed. Document the final internal fields/blocker in TECHNICAL_DESIGN.md in the implementation commit.

## Planned tests

`code/tests/test_required_record_preservation.py` must exercise actual obligation and planner behavior for:
1. absent required tombstone and absent required retained backup (baseline incorrectly permits COMPLETE);
2. unknown required presence, kept distinct from proven absence;
3. present stable-reference tombstone with PII removed; missing required stable reference must not pass;
4. present retained backup, restore blocked versus restore allowed;
5. another preserve-and-treat record (e.g. shared support conversation) cannot silently be treated as DELETE;
6. planner/validator agree on a blocked result without inventing a finding, operation or evidence ID.

Keep these fictional counterexamples small. No live provider is needed to establish the failure or fix.
