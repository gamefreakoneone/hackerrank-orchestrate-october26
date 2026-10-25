# Spec 0017 — Replica state and proof: requirements

**Status:** Not started. **Depends on:** 0010, 0012, 0016 (implemented baseline).
Read `../../CORRECTIVE_HANDOFF.md` and implementation-review finding 1 first.

## Goal

Prevent a primary-only absence or clean record from hiding an uncleared physical copy.

## Acceptance criteria

- Determine the latest established state and identifying fields for each relevant, identified physical copy
  before combining them into the resource's obligation. Preserve physical-copy provenance through the planner.
- A primary-only 404 cannot clear a replica previously observed present. A clean primary cannot hide exposed
  identifiers in a replica. Later evidence clearing that same replica can supersede its older state.
- All evidence must be available at `audit_at`. Distinguish observation time from file availability and a row's
  last-update metadata; newer packaging of an older observation must not silently overwrite newer state.
- In a single file/trace, a later observation of the same copy supersedes an earlier one. Across different
  copies, an outstanding policy violation wins over a clean copy. Unestablished required state remains UNKNOWN.
- Evidence-format labels (`export`, `bundle`, `screen`, `service_read`) are not automatically independent
  storage-copy identities, nor permission to clear every physical replica. Scope must come from evidence.
- A citation supports the assertion being emitted. Retain the other contributing proof IDs in diagnostics;
  do not generate duplicate CSV steps merely to represent several copies or fabricate broader coverage.
- Preserve the seven output fields, canonical ordering, grounding/cutoff rules and existing schema.
- Reproduce the audit counterexamples before the fix and demonstrate passing focused tests afterwards.
  Record comparable sample metrics and explain contract-required regressions; do not alter sample answers.

## Boundaries

Use the existing ledger, facts and planner. Extend only the data needed to carry per-copy state and proof.
No new model calls, provider, generic provenance framework or unrelated cleanup is required. Spec 0018 owns
whether a treated record must remain present; this spec makes the evidence available to evaluate that correctly.
