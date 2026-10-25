# Spec 0018 — Required record preservation: requirements

**Status:** Not started. **Depends on:** 0017.
Read implementation-review finding 2 and the supplied record-treatment operations.

## Goal

Treat required preservation and required removal of identifying data/restoration access as separate predicates.

## Acceptance criteria

- A policy-required tombstone must remain available with its permitted stable reference and prohibited direct
  identifiers removed. A required retained backup must remain available with restoration appropriately blocked.
- Absence is not blanket satisfaction of REDACT, ANONYMIZE or a retained BACKUP_ARCHIVE obligation. Derive
  preservation from the applicable rule/action; do not hardcode individual resources or change supplied rules.
- A missing required record cannot produce COMPLETE, VERIFY_RECORD_REDACTED or VERIFY_RESTORE_BLOCKED as a
  claim of current compliance. Distinguish known absence from unknown preservation state.
- Present, correctly treated tombstones and retained backups still pass. Keep expected stable references;
  do not weaken redaction/anonymization requirements in order to satisfy preservation.
- Use existing allowed output operations and fields. No invented restore/recreate operation or false finding
  is permitted when the schema has no remediation operation for a missing retained record.
- Add an explicit internal preservation blocker when required. Integrate it consistently with the planner,
  diagnostics and validator; retain future verification checks with empty evidence for INCOMPLETE cases.
- Record before/after sample results and passing regression tests. Supplied sample answers remain unchanged.

## Boundaries

Fix the actual `SATISFYING`/obligation/planner path. Do not reinterpret absence of a non-retained process as
missing retained business data. No new policy language, external store or model-based policy engine is needed.
