# Spec 0015 — full-run-ablations-reports: requirements

**Depends on:** 0014

## Goal

Final cold-cache full run, ablations, and the two required evaluation reports.

## Requirements / acceptance criteria

- Cold-cache run (`--no-cache`) over 518 cases writes root `output.csv`; validator clean.
- Ablations on samples: deterministic-only (`--offline`, no LLM), no historical identifiers, trust activity claims.
- `code/evaluation/evaluation_report.md`: status accuracy, step- and field-level accuracy, sequence accuracy
  (exact + LCS) on the 32 samples labelled as a **regression set** (dev/holdout both inspected in Phase 0); held-out
  evidence = synthetic cases + metamorphic tests; completion-blocker and activity-citation counts; failures found
  and improvements made (commit refs, before/after numbers from each spec's status.md), ablation table.
- `code/evaluation/usage_report.md` from the final run's ledger: providers, models, calls, input/output tokens,
  total and average tokens per request, estimated cost total and per request, per model and overall.

## Out of scope

Anything owned by another spec in `code/docs/FEATURE_STATUS.md`. Hard rules in `CLAUDE.md` apply.
