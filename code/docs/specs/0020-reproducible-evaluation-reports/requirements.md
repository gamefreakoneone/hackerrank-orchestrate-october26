# Spec 0020 — Reproducible evaluation reports: requirements

**Status:** Completed. **Depends on:** 0019.

## Goal

Make evaluation claims traceable to preserved inputs and rebuild reports without new model calls.

## Acceptance criteria

- Derive status, linkage, step/field and sequence claims from per-case scorer results. Remove unsupported
  template claims such as every grounded sample having an exact plan. Explicitly label metric denominators.
- Identify state/citation checks that receive gold resources/operations as oracle-assisted component diagnostics,
  not end-to-end discovery or hidden-answer accuracy. Keep samples/custom tests labelled as inspected validation.
- Preserve the minimum evaluated prediction, diagnostics, ablation and custom-result artifacts with revision,
  configuration and hashes. Report generation must not depend on an unrecorded, ignored `runs/` directory.
- Missing or mismatched required artifacts must raise an actionable error and exit nonzero. Do not silently
  substitute another run, invent metrics, or invoke models to rebuild a report.
- Correct README/checklist validation commands to pass the matching diagnostics. The saved baseline validates
  with 0 errors/104 warnings only with `code/evaluation/final_run/diagnostics.jsonl`; retain that historical context.
- Distinguish implementation completion, unmet acceptance criteria, unavailable measurements and publication
  status. Report the original discovery target gap explicitly until evidence closes it.
- Usage summaries come from the selected ledger; pricing remains labelled estimated/unverified unless its
  source was actually verified. Do not alter recorded calls/tokens to fit a cost narrative.
- Preserve the currently selected full-run bundle while testing the new report path. Intermediate corrected
  sample results must not be presented as the results that produced the old root output.

## Boundaries

Extend the existing scorer, report generator and custom runner. No dashboard, reporting framework, extra model
or new analytics service is needed. Only retain artifacts necessary to reproduce the stated measurements.
