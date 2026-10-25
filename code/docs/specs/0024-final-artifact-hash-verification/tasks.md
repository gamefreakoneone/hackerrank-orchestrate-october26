# Spec 0024 — Final artifact hash verification: tasks

- [x] Verify 0023 is completed/pushed; read this spec and review M2.
- [x] Capture before/dev metrics and reproduce both accepted wrong-hash artifacts using temporary copies.
- [x] Verify all required final artifact hashes before parsing/rendering, with explicit failures.
- [x] Update existing fixtures and add altered-content, missing-hash and preservation checks through the real CLI.
- [x] Rebuild the preserved reports in a separate directory and compare their bytes; never overwrite selected reports.
- [x] Run focused checks and comparable after/dev scoring; record actual results.
- [x] Update status/tasks/FEATURE_STATUS/MORNING_REPORT and relevant README integrity wording; log and verify trace.
- [x] Commit `spec 0024: verify every final artifact hash`, push and verify before 0025.

## Validation commands

RUN_LIVE unset. All corruption experiments use temporary fixture copies.

```text
python code/evaluation/run_eval.py --split all --out runs/corrective/0024_before.csv -- --offline --no-cache
python code/evaluation/score.py runs/corrective/0024_before.csv dataset/sample_output.csv --split dev --diagnostics runs/corrective/0024_before.diagnostics.jsonl
python -m pytest code/tests/test_report_reproducibility.py code/tests/test_run_publication.py code/tests/test_packaging_integrity.py -q
python code/evaluation/make_reports.py --report-output-directory runs/corrective/0024_rebuilt
python code/evaluation/run_eval.py --split all --out runs/corrective/0024_after.csv -- --offline --no-cache
python code/evaluation/score.py runs/corrective/0024_after.csv dataset/sample_output.csv --split dev --diagnostics runs/corrective/0024_after.diagnostics.jsonl
git diff --check
```

Add the byte-comparison command/output to status.md. A Windows symlink/encoding failure in packaging tests is an
actual failed check to diagnose, not permission to silently skip it or claim Linux results were reproduced.
