# Spec 0009 — vision-extraction: tasks

- [x] vision.py + prompt
- [x] revalidation
- [x] tests with recorded cached responses
- [x] spot-check 3 PNGs by eye and record in status.md
- [x] Update FEATURE_STATUS.md, status.md, this file; commit `spec 0009: <summary>`

## Validation commands

```bash
python -m pytest code/tests/test_vision.py -q
python code/tools/evidence_coverage.py --png
python code/evaluation/run_eval.py --split dev
```
