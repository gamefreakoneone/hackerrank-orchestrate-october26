# Spec 0021 — Validated final run and packaging: tasks

- [ ] Confirm 0020 is completed/pushed; capture before metrics and preserve the existing selected run.
- [ ] Implement candidate-first publication, explicit manifest output and the thin finalizer; document paths.
- [ ] Add planned failure/packaging regression tests and run required checks with `RUN_LIVE` unset.
- [ ] If runtime changed, commit/push an In progress code-freeze checkpoint and record its actual SHA.
- [ ] Refresh the 0020 default/ablation/custom evaluation-input bundle from that frozen code and record hashes.
- [ ] Run/validate the cold full candidate, finalize the matching artifacts/reports and rebuild the package.
- [ ] Capture after metrics; verify the extracted package layout and model-free report rebuild.
- [ ] Update status/tasks/FEATURE_STATUS, MORNING_REPORT, SUBMISSION_CHECKLIST and interview notes; append log
      and export/verify trace. Label remaining limitations and incomplete evidence accurately.
- [ ] Commit `spec 0021: validate final run and submission bundle`, push and verify publication. Report actual
      branch/SHA and selected-run provenance. Do not submit automatically.

## Validation commands

The new test files, main.py manifest option and finalizer below are planned deliverables of this spec.
The evaluation-input manifest is produced by the 0020 workflow and must be refreshed for the frozen code.

```text
python code/evaluation/run_eval.py --split all --out runs/corrective/0021_before.csv
python code/evaluation/score.py runs/corrective/0021_before.csv dataset/sample_output.csv --split dev --diagnostics runs/corrective/0021_before.diagnostics.jsonl
python -m pytest code/tests/test_run_publication.py code/tests/test_packaging_integrity.py -q
python -m pytest code/tests -q
python code/evaluation/run_custom.py
python code/main.py --cases all --no-cache --out runs/corrective/0021_candidate.csv --run-manifest-output runs/corrective/0021_candidate.manifest.json
python -c "import sys;sys.path.insert(0,'code');from ghostaudit.validate import cli;cli()" runs/corrective/0021_candidate.csv --diagnostics runs/corrective/0021_candidate.diagnostics.jsonl
python code/evaluation/run_eval.py --split all --out runs/corrective/0021_after.csv
python code/evaluation/score.py runs/corrective/0021_after.csv dataset/sample_output.csv --split dev --diagnostics runs/corrective/0021_after.diagnostics.jsonl
python code/tools/finalize_run.py --candidate-manifest runs/corrective/0021_candidate.manifest.json --evaluation-inputs code/evaluation/corrective_run/evaluation_inputs.json
python -c "import sys;sys.path.insert(0,'code');from ghostaudit.validate import cli;cli()" output.csv --diagnostics code/evaluation/final_run/diagnostics.jsonl
python code/evaluation/make_reports.py --final-manifest code/evaluation/final_run/manifest.json
python code/tools/make_zip.py
git diff --check
```

Run the full suite once after runtime changes settle; repeat only when a subsequent change/failure warrants it.
Stage newly generated allowed artifact files before make_zip.py (it selects tracked/staged code files); inspect
the staged paths so caches, `.env`, dataset and unrelated files never enter the package. Record the clean-room
commands and results in status.md. Do not call report/zip generation successful solely because old files exist.
