# Spec 0020 — Reproducible evaluation reports: design

## Owned files and artifact contract

Use `evaluation/score.py`, `make_reports.py`, `run_eval.py`, `run_custom.py`, README and the submission checklist.
Keep `sample_output.csv` an evaluation oracle only. Existing final-run files remain historical until 0021.

Create a small JSON `evaluation_inputs.json` manifest referencing relative paths, SHA-256 values, producing
code revisions and configuration labels for:
- the default sample predictions and their matching diagnostics;
- each executed ablation's predictions/diagnostics and its explicit mode;
- structured custom-validation outcomes (add JSON alongside the existing Markdown result);
- recorded test-command outcomes, distinguishing actual execution from an absent/unavailable result.

Preserve the actual corrective sample inputs under `code/evaluation/corrective_run/`, separate from the selected
`final_run/`. Git history/status snapshots preserve earlier measurements. Do not copy caches, credentials or the
whole dataset into this bundle. Missing optional measurements are labelled not measured; required measurements
for final readiness cannot be silently omitted.

Extend `make_reports.py` to load these references from the selected manifest or an explicit
`--evaluation-inputs PATH` argument (planned), and add `--report-output-directory DIR` (planned) for staging
reports without replacing the selected ones. Keep the existing `--final-manifest` input. The two inputs must
identify their real producing revisions: mismatches must be explicit and cannot claim a unified final release.
0021 will pass a same-code final-run/evaluation bundle and promote it only after validation.

Validate required paths, hashes, case coverage, paired diagnostics and declared run/configuration before
rendering. Reuse existing scorer/ledger functions, with verbose names for artifact roles. Derive narrative
claims from computed values (including the exact-plan count among grounded cases). Preserve original model
usage; no LLM/provider call belongs in report generation.

## Planned tests

Add `code/tests/test_report_reproducibility.py` with a self-contained fictional fixture bundle:
- regenerate the same metrics/reports without an existing `runs/`, cache, credentials or model access;
- missing predictions, missing diagnostics, wrong hashes, wrong request coverage and mismatched declared
  revisions/configurations fail explicitly instead of rendering a misleading ready report;
- fewer exact plans than grounded accounts produces accurate prose;
- report staging leaves selected reports untouched;
- structured custom results and ledger totals, not hardcoded narrative numbers, drive the report.

Use source fixtures sufficient for those behaviors, not copies of the implementation's calculations. Document
the actual artifact-capture and offline rebuild commands in README. Do not rewrite the historical overnight scores.
