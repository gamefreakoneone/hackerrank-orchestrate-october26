# Spec 0018 — Required record preservation: tasks

- [x] Complete and publish 0017; read all four files of 0018 and the applicable supplied rules.
- [x] Capture before metrics and reproduce missing-tombstone/missing-backup false compliance.
- [x] Implement explicit presence-plus-treatment checks and shared blocker handling.
- [x] Add planned preservation tests and update affected existing tests/contracts.
- [x] Run checks and capture after metrics; explain correctness-driven sample differences.
- [x] Update status/tasks/FEATURE_STATUS, design and morning report; append log and verify trace export.
- [x] Commit `spec 0018: enforce required record preservation`, push and verify remote publication before 0019.

## Validation commands

```text
python code/evaluation/run_eval.py --split all --out runs/corrective/0018_before.csv
python code/evaluation/score.py runs/corrective/0018_before.csv dataset/sample_output.csv --split dev --diagnostics runs/corrective/0018_before.diagnostics.jsonl
python -m pytest code/tests/test_required_record_preservation.py code/tests/test_policy.py code/tests/test_obligations.py code/tests/test_validate.py code/tests/test_pipeline_e2e.py -q
python code/evaluation/run_eval.py --split all --out runs/corrective/0018_after.csv
python code/evaluation/score.py runs/corrective/0018_after.csv dataset/sample_output.csv --split dev --diagnostics runs/corrective/0018_after.diagnostics.jsonl
git diff --check
```

The new test file is planned work in this spec. Use matching configurations for before/after, with offline
unit tests and no unrequested full-dataset run. Follow the handoff's commit/log/trace/publication checks.
