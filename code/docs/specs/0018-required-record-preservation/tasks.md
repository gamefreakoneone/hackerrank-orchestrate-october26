# Spec 0018 — Required record preservation: tasks

- [ ] Complete and publish 0017; read all four files of 0018 and the applicable supplied rules.
- [ ] Capture before metrics and reproduce missing-tombstone/missing-backup false compliance.
- [ ] Implement explicit presence-plus-treatment checks and shared blocker handling.
- [ ] Add planned preservation tests and update affected existing tests/contracts.
- [ ] Run checks and capture after metrics; explain correctness-driven sample differences.
- [ ] Update status/tasks/FEATURE_STATUS, design and morning report; append log and verify trace export.
- [ ] Commit `spec 0018: enforce required record preservation`, push and verify remote publication before 0019.

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
