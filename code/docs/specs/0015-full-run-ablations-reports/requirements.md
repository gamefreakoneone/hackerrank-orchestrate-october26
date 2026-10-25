# Spec 0015 — full-run-ablations-reports: requirements

**Depends on:** 0014

## Goal

Final cold-cache full run, ablations, and the two required evaluation reports.

## Requirements / acceptance criteria

- Cold-cache run (`--no-cache`) over 518 cases writes root `output.csv`; validator clean.
- Ablations on samples: deterministic-only (`--offline`, no LLM), no historical identifiers, trust activity claims,
  `--ungrounded-account-steps ranked` (emit the top-ranked account in INCOMPLETE output, every such step labelled a
  guessed link in diagnostics and the report; report its linkage and step effects — never allowed to produce
  COMPLETE, never the submitted default).
- `code/evaluation/evaluation_report.md`: status accuracy, step- and field-level accuracy, sequence accuracy
  (exact + LCS) on the 32 samples labelled as a **regression set** (dev/holdout both inspected in Phase 0); account
  linkage accuracy as its own row; custom and metamorphic validation results (not a holdout); blocker counts;
  failures found
  and improvements made (commit refs, before/after numbers from each spec's status.md), ablation table.
- `code/evaluation/usage_report.md` from the final run's ledger: providers, models, calls, input/output tokens,
  total and average tokens per request, estimated cost total and per request, per model and overall.

## Out of scope

Anything owned by another spec in `code/docs/FEATURE_STATUS.md`. Hard rules in `CLAUDE.md` apply.
