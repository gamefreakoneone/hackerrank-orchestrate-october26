# Spec 0023 — Unknown copy treatment: tasks

- [ ] Verify 0022 is completed/pushed; read this spec and review M1.
- [ ] Capture comparable before/dev metrics and reproduce both missing-treatment-copy counterexamples.
- [ ] Represent every relevant copy and aggregate uncertainty without suppressing established violations.
- [ ] Update internal diagnostics/flags/contracts and direct consumers; remove superseded selection logic.
- [ ] Add planned regressions and run focused checks plus after/dev scoring.
- [ ] Measure affected obligations using participant evidence; label parser/vision configuration and scope.
- [ ] Update status/tasks/FEATURE_STATUS/MORNING_REPORT; append log and export/verify the trace.
- [ ] Commit `spec 0023: preserve unknown treatment for every copy`, push and verify before 0024.

## Validation commands

RUN_LIVE unset; new test file is planned. Keep both sample passes offline/no-cache.

```text
python code/evaluation/run_eval.py --split all --out runs/corrective/0023_before.csv -- --offline --no-cache
python code/evaluation/score.py runs/corrective/0023_before.csv dataset/sample_output.csv --split dev --diagnostics runs/corrective/0023_before.diagnostics.jsonl
python -m pytest code/tests/test_unknown_copy_treatment.py code/tests/test_required_record_preservation.py code/tests/test_replica_state.py code/tests/test_obligations.py code/tests/test_validate.py code/tests/test_pipeline_e2e.py -q
python code/evaluation/run_eval.py --split all --out runs/corrective/0023_after.csv -- --offline --no-cache
python code/evaluation/score.py runs/corrective/0023_after.csv dataset/sample_output.csv --split dev --diagnostics runs/corrective/0023_after.diagnostics.jsonl
git diff --check
```

Preserve selected artifacts. Do not use saved obligation lists as prediction inputs; they are comparison artifacts only.
