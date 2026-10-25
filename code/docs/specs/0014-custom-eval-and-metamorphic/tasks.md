# Spec 0014 — custom-eval-and-metamorphic: tasks

- [x] overlay runner + --data-root
- [x] ≥7 cases with rationale
- [x] metamorphic tests
- [x] results table in status.md
- [x] Update FEATURE_STATUS.md, status.md, this file; commit `spec 0014: <summary>`

## Validation commands

```bash
python code/evaluation/run_custom.py
python -m pytest code/tests/test_metamorphic.py -q
```
