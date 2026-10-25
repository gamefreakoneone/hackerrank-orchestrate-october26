# Spec 0012 — planner-and-evidence: requirements

**Depends on:** 0004, 0011

## Goal

Status decision, full step plan, deterministic evidence citation; end-to-end on samples.

## Requirements / acceptance criteria

- status = COMPLETE iff (no completion blocker) and (≥1 obligation) and (every obligation satisfied with proof);
  else INCOMPLETE. Completion blockers and exact output (TECHNICAL_DESIGN §3.5):
  ACCOUNT_UNGROUNDED ⇒ INCOMPLETE, no account steps (ranked candidates in diagnostics only), other obligations
  planned normally; UNKNOWN_STATE obligation ⇒ unsatisfied, no finding/remediation for it, VERIFICATION step with
  `""`; POLICY_UNDEFINED ⇒ INCOMPLETE, no step for that resource; EMPTY_OBLIGATIONS ⇒ INCOMPLETE with `[]`;
  ACCOUNT_MULTI_GROUNDED / CONDITION_DEFAULTED / ACTIVITY_CITATION ⇒ not blockers, flagged.
  Every flag is written to diagnostics and counted by the scorer report.
- INCOMPLETE: findings (cited) + remediation (empty) for unsatisfied obligations; verification (empty) for **all**
  obligations. COMPLETE: verification for all obligations, each citing its proof.
- Evidence rule (Phase-0b): cite the latest eligible file that **establishes** the cited state for that system:
  (1) observed state: latest eligible file with an observation of the resource showing that state;
  (2) absence by omission: eligible `SnapshotCoverage` of the system not containing the resource; drop snapshots
  superseded by the resource's last DELETE_RECORD activity ≤ audit_at; take the latest with replica coverage, else
  the latest (TECHNICAL_DESIGN §5 Q2; chosen post hoc, 4/4 on 4 points; `code/tools/p0_q2b_coverage.py` asserts it
  and shows the 0b "most copies" rule was 3/4);
  (3) fallback only if no file establishes it: a state-check activity (CHECK_DATA_FLOW / CHECK_RESTORE_ACCESS) or an
  `audit_id` ≤ audit_at, flagged `ACTIVITY_CITATION`. Operational-claim activities are never cited.
- An obligation with no establishing evidence is UNKNOWN_STATE (never cited from a non-establishing file).
- Targets (regression set): step F1 ≥ 0.80 on dev; status accuracy reported next to linkage accuracy. Status is
  capped at 23/32 on samples while 9 gold-COMPLETE cases lack a grounded account link — do not relax grounding to
  raise it.

## Out of scope

Anything owned by another spec in `code/docs/FEATURE_STATUS.md`. Hard rules in `CLAUDE.md` apply.
