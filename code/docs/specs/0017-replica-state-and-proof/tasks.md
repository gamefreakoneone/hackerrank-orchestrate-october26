# Spec 0017 — Replica state and proof: tasks

- [ ] Read the four spec files, handoff, baseline review and affected runtime/tests.
- [ ] Record comparable before metrics; reproduce the two cross-copy false-COMPLETE cases.
- [ ] Implement scoped per-copy state and treatment evaluation with proof diagnostics.
- [ ] Add the planned regression tests; update affected callers/contracts and remove superseded logic.
- [ ] Run focused checks and record after metrics, including justified differences from sample gold.
- [ ] Update status/tasks/FEATURE_STATUS, Key Contracts and MORNING_REPORT; append log and verify trace export.
- [ ] Commit `spec 0017: correct replica state and proof aggregation`, push, and verify remote publication
      before starting 0018. Record the actual branch/SHA; a failed check or push is not saved completion.

## Validation commands

Run from the repository root. The new test file is implemented by this spec. Keep `RUN_LIVE` unset for tests.

```text
python code/evaluation/run_eval.py --split all --out runs/corrective/0017_before.csv
python code/evaluation/score.py runs/corrective/0017_before.csv dataset/sample_output.csv --split dev --diagnostics runs/corrective/0017_before.diagnostics.jsonl
python -m pytest code/tests/test_replica_state.py code/tests/test_timeline.py code/tests/test_obligations.py code/tests/test_pipeline_e2e.py -q
python code/evaluation/run_eval.py --split all --out runs/corrective/0017_after.csv
python code/evaluation/score.py runs/corrective/0017_after.csv dataset/sample_output.csv --split dev --diagnostics runs/corrective/0017_after.diagnostics.jsonl
git diff --check
```

Capture `before` before edits. A missing model/cache prerequisite must be recorded; do not mislabel a degraded
offline run as comparable to the live baseline. The new counterexample test should fail before its fix.
