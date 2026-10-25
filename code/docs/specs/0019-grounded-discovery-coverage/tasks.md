# Spec 0019 — Grounded discovery coverage: tasks

- [ ] Verify 0018 is complete/pushed; read this spec and the existing discovery code/report.
- [ ] Capture before sample metrics and discovery provenance with a documented image-cache configuration.
- [ ] Investigate the measured misses; record the gap table and supported conclusions.
- [ ] Implement only justified parser/reference changes, or document the investigation-only outcome.
- [ ] Verify exact matching, decoys, cutoff and repeated/historical-account behavior; capture after metrics.
- [ ] Update status/tasks/FEATURE_STATUS and MORNING_REPORT; append log and verify trace export.
- [ ] Commit `spec 0019: measure and improve grounded discovery` (describe no-improvement honestly if applicable),
      push and verify the commit before 0020.

## Validation commands

```text
python code/evaluation/run_eval.py --split all --out runs/corrective/0019_before.csv
python code/evaluation/score.py runs/corrective/0019_before.csv dataset/sample_output.csv --split dev --diagnostics runs/corrective/0019_before.diagnostics.jsonl
python code/tools/discovery_report.py --split all --verbose
python -m pytest code/tests/test_grounded_discovery_regressions.py code/tests/test_discovery.py code/tests/test_identity.py -q
python code/evaluation/run_eval.py --split all --out runs/corrective/0019_after.csv
python code/evaluation/score.py runs/corrective/0019_after.csv dataset/sample_output.csv --split dev --diagnostics runs/corrective/0019_after.diagnostics.jsonl
python code/tools/discovery_report.py --split all --verbose
git diff --check
```

The additional regression file and gap-review document are planned deliverables. Preserve the first and second
discovery summaries with their revisions; do not substitute reported historical numbers for missing runs.
