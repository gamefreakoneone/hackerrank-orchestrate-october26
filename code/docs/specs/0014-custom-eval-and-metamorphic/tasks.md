# Spec 0014 — custom-eval-and-metamorphic: tasks

- [ ] overlay runner + --data-root
- [ ] ≥7 cases with rationale
- [ ] metamorphic tests
- [ ] results table in status.md
- [ ] Update FEATURE_STATUS.md, status.md, this file; commit `spec 0014: <summary>`

## Validation commands

```bash
python code/evaluation/run_custom.py
python -m pytest code/tests/test_metamorphic.py -q
```
