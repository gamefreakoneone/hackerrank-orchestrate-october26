# Spec 0022 — Observation-time cutoffs: tasks

- [x] Sync the named branch and read all four spec files, the new handoff and review B1.
- [x] Capture an offline/no-cache sample baseline; record configuration and revision.
- [x] Reproduce both account errors and demonstrate failing fictional temporal regressions on the baseline.
- [x] Inventory temporal influence paths; implement cutoff-safe observations and coverage without backdating.
- [x] Update consumers, parser cache version where needed, Key Contracts and decision log.
- [x] Run focused checks, the affected-case assessment and comparable after/dev scoring; explain differences.
- [x] Update status/tasks/FEATURE_STATUS/MORNING_REPORT, append log, export and verify the actual harness trace.
- [x] Commit `spec 0022: enforce observation-time cutoffs`, push and verify publication before 0023.

## Validation commands

From the repository root, with RUN_LIVE unset. The new test file is planned implementation.

```text
python code/evaluation/run_eval.py --split all --out runs/corrective/0022_before.csv -- --offline --no-cache
python code/evaluation/score.py runs/corrective/0022_before.csv dataset/sample_output.csv --split dev --diagnostics runs/corrective/0022_before.diagnostics.jsonl
python -m pytest code/tests/test_observation_cutoffs.py code/tests/test_timeline.py code/tests/test_replica_state.py code/tests/test_discovery.py code/tests/test_identity.py code/tests/test_pipeline_e2e.py -q
python code/evaluation/run_eval.py --split all --out runs/corrective/0022_after.csv -- --offline --no-cache
python code/evaluation/score.py runs/corrective/0022_after.csv dataset/sample_output.csv --split dev --diagnostics runs/corrective/0022_after.diagnostics.jsonl
git diff --check
```

Add the exact bounded affected-case reproduction command and output to status.md when run. No full live pipeline
is authorized by these tasks. Offline/no-cache results are not interchangeable with the preserved live sample score.
