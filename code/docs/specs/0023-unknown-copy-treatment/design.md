# Spec 0023 — Unknown copy treatment: design

## Owned files

`ghostaudit/obligations.py`, affected internal models and consumers in `pipeline.py`, `planner.py`, `validate.py`;
`timeline.py` only where needed to expose the existing per-copy evidence accurately.

1. Form the relevant copy set from both presence and treatment facts. For each copy, determine known absence,
   known enabled/restorable treatment, or unresolved treatment. Preserve temporal precedence from 0022 and the
   0018 same-copy absence behavior.
2. Carry UNKNOWN for a present copy lacking the required treatment fact. Use a clear diagnostic reason and the
   presence evidence as provenance of the uncertainty, not as proof that treatment has occurred.
3. Aggregate with separate questions: is a violation established, is any required treatment unknown, and is required
   preservation established? All must support compliance before satisfied=True. Known violations retain their
   finding proofs even when another copy is unknown; do not let UNKNOWN suppress a real finding.
4. Reuse UNKNOWN_STATE/blocker handling where possible. If an aggregate ACTIVE state would hide a second copy's
   uncertainty from diagnostics, update the direct flag consumer rather than adding a redundant status family.
5. COMPLETE proofs must establish the claimed treatment and required presence. Never cite a plain inventory row
   as proof of blocked restore access. Preserve all contributing per-copy proofs in diagnostics.
6. Update Key Contracts and remove superseded treatment-only copy selection.

## Baseline counterexample

At one eligible snapshot time, a resource has two SQL observations:

| Copy | DATA_FLOW fields | BACKUP_ARCHIVE fields |
|---|---|---|
| primary | enabled=false | restore_allowed=false |
| failover_replica | record present, enabled unspecified | archive present, restore_allowed unspecified |

Both observations link to the same fictional subject. Baseline presence has both copies, but CopyState contains
only primary; build_obligation is satisfied. This is a component counterexample, not proof that a saved row is wrong.
The earlier non-PDF/non-PNG scan found no analogous missing-treatment copy among saved flow/backup obligations;
complete live-configuration impact remains unmeasured.

Add `code/tests/test_unknown_copy_treatment.py` (planned). Test the real state→obligation→planner path and at least
one assessment/flag integration path with a grounded compliant account. Resolve the replica in a second fixture
and assert compliance becomes possible, so the negative test is not merely blocked by unrelated account linkage.
