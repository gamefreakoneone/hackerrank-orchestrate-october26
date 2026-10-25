# Spec 0012 — planner-and-evidence: requirements

**Depends on:** 0004, 0011

## Goal

Status decision, full step plan, deterministic evidence citation; end-to-end on samples.

## Requirements / acceptance criteria

- status = COMPLETE iff every obligation satisfied, else INCOMPLETE.
- INCOMPLETE: findings (cited) + remediation (empty) for unsatisfied obligations; verification (empty) for **all**
  obligations. COMPLETE: verification for all obligations, each citing its proof.
- Evidence rule (Phase-0 Q2): latest eligible file (by captured_at) that mentions the resource; if none, latest
  eligible full_table snapshot of the logical system; never a file captured after audit_at; never activity/audit ids.
- A COMPLETE obligation without citable proof ⇒ treat as UNKNOWN and report it in a diagnostics file (not silently cite).
- Target: dev split status accuracy ≥ 90%, step F1 ≥ 0.80.

## Out of scope

Anything owned by another spec in `code/docs/FEATURE_STATUS.md`. Hard rules in `CLAUDE.md` apply.
