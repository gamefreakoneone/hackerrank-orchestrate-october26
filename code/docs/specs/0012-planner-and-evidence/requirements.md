# Spec 0012 — planner-and-evidence: requirements

**Depends on:** 0004, 0011

## Goal

Status decision, full step plan, deterministic evidence citation; end-to-end on samples.

## Requirements / acceptance criteria

- status = COMPLETE iff (no completion blocker) and (≥1 obligation) and (every obligation satisfied with proof);
  else INCOMPLETE. Completion blockers and exact output (TECHNICAL_DESIGN §3.5):
  UNRESOLVED_ACCOUNT ⇒ INCOMPLETE, no account steps, other obligations planned normally;
  UNKNOWN_STATE obligation ⇒ unsatisfied, no finding/remediation for it, VERIFICATION step with `""`;
  EMPTY_OBLIGATIONS ⇒ INCOMPLETE with `[]`; ACCOUNT_LINK_DEFAULT ⇒ not a blocker, planned normally, flagged.
  Every flag is written to diagnostics and counted by the scorer report.
- INCOMPLETE: findings (cited) + remediation (empty) for unsatisfied obligations; verification (empty) for **all**
  obligations. COMPLETE: verification for all obligations, each citing its proof.
- Evidence rule (Phase-0b): cite the latest eligible file that **establishes** the cited state for that system:
  (1) observed state: latest eligible file with an observation of the resource showing that state;
  (2) absence by omission: `SnapshotCoverage` of the system captured after the resource's last DELETE_RECORD
  activity (if any) and ≤ audit_at, not containing the resource; prefer most physical copies covered, then latest
  (fits 4/4 sample omission citations: case_04 → evidence_54 primary+failover over evidence_90 primary-only;
  case_31 → evidence_51 because evidence_54/evidence_90 predate the 09-06 deletion);
  (3) fallback only if no file establishes it: an `activity_id` / `audit_id` ≤ audit_at whose content states the
  result (e.g. CHECK_DATA_FLOW, CHECK_RESTORE_ACCESS), flagged `ACTIVITY_CITATION`.
- An obligation with no establishing evidence is UNKNOWN_STATE (never cited from a non-establishing file).
- Target: dev split status accuracy ≥ 90%, step F1 ≥ 0.80.

## Out of scope

Anything owned by another spec in `code/docs/FEATURE_STATUS.md`. Hard rules in `CLAUDE.md` apply.
