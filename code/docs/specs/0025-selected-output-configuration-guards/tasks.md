# Spec 0025 — Selected-output configuration guards: tasks

- [ ] Verify 0024 is completed/pushed; read this spec and review M3.
- [ ] Capture before/dev metrics; reproduce unsafe selected-path modes in an isolated test fixture.
- [ ] Implement early selected-output configuration validation and finalizer mode refusals.
- [ ] Add negative/positive path-alias, sample, selector, custom-root, offline and ablation tests; preserve provenance.
- [ ] Update README safe commands, Key Contracts and decision log.
- [ ] Run focused checks, comparable after/dev scoring, then the full offline suite once code settles.
- [ ] Rebuild the preserved reports into scratch space and inspect a fresh archive without promoting new predictions.
- [ ] Record implementation results and separate release-regeneration status; ask before any live run.
- [ ] Update status/tasks/FEATURE_STATUS/MORNING_REPORT; append log and export/verify the trace.
- [ ] Commit `spec 0025: guard selected output from non-release runs`, push and verify remote publication.

## Validation commands

From repository root, RUN_LIVE unset. All selected-path failure experiments use isolated fixtures.

```text
python code/evaluation/run_eval.py --split all --out runs/corrective/0025_before.csv -- --offline --no-cache
python code/evaluation/score.py runs/corrective/0025_before.csv dataset/sample_output.csv --split dev --diagnostics runs/corrective/0025_before.diagnostics.jsonl
python -m pytest code/tests/test_run_publication.py code/tests/test_packaging_integrity.py -q
python code/evaluation/run_eval.py --split all --out runs/corrective/0025_after.csv -- --offline --no-cache
python code/evaluation/score.py runs/corrective/0025_after.csv dataset/sample_output.csv --split dev --diagnostics runs/corrective/0025_after.diagnostics.jsonl
python -m pytest code/tests -q
python code/evaluation/make_reports.py --report-output-directory runs/corrective/0025_rebuilt
python code/tools/make_zip.py --output runs/corrective/0025_code.zip
git diff --check
```

The archive contains corrected code and the preserved historical release reports until authorized regeneration;
building it is a packaging check, not a claim of a refreshed submission. Do not rerun the full suite without a new
change/failure reason. Record platform failures rather than copying the old 163-passed claim.
