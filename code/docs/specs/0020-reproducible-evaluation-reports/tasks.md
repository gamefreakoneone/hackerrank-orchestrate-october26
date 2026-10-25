# Spec 0020 — Reproducible evaluation reports: tasks

- [ ] Verify 0019 is complete/pushed; record before metrics and inspect every generated report claim.
- [ ] Implement input manifest validation, persisted evaluation/custom inputs and staged report generation.
- [ ] Replace hardcoded/overstated claims; distinguish oracle-assisted diagnostics and unmet acceptance criteria.
- [ ] Correct README/checklist validator commands and document offline report rebuilding.
- [ ] Add planned reproducibility tests, including explicit failures and report-staging preservation.
- [ ] Capture actual default/ablation/custom inputs under corrective_run with hashes/revisions; never label these
      intermediate metrics as the run that produced the old selected full output.
- [ ] Record after metrics, update status/tasks/FEATURE_STATUS and MORNING_REPORT, append log and verify trace.
- [ ] Commit `spec 0020: make evaluation reports reproducible and accurate`, push and verify before 0021.

## Validation commands

```text
python code/evaluation/run_eval.py --split all --out runs/corrective/0020_before.csv
python code/evaluation/score.py runs/corrective/0020_before.csv dataset/sample_output.csv --split dev --diagnostics runs/corrective/0020_before.diagnostics.jsonl
python -m pytest code/tests/test_report_reproducibility.py code/tests/test_score.py code/tests/test_validate.py -q
python code/evaluation/run_eval.py --split all --out runs/corrective/0020_after.csv
python code/evaluation/score.py runs/corrective/0020_after.csv dataset/sample_output.csv --split dev --diagnostics runs/corrective/0020_after.diagnostics.jsonl
python code/evaluation/run_eval.py --split all --out runs/corrective/0020_deterministic.csv -- --offline --no-cache
python code/evaluation/run_eval.py --split all --out runs/corrective/0020_no_history.csv -- --ablate no-history
python code/evaluation/run_eval.py --split all --out runs/corrective/0020_trust_claims.csv -- --ablate trust-claims
python code/evaluation/run_eval.py --split all --out runs/corrective/0020_ranked_accounts.csv -- --ungrounded-account-steps ranked
python code/evaluation/run_custom.py
git diff --check
```

The new test file and report CLI options are planned implementation. The fixture test must invoke the actual
report CLI and prove rebuilding is model-free. Retain the execution/configuration distinction between the
deterministic ablation and the default; do not run a full 518-case job in this spec.
