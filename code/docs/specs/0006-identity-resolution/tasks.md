# Spec 0006 — identity-resolution: tasks

- [x] identity.py
- [x] tests: current email, historical email (case_10/12/29), post-audit change ignored, hash recompute, decoy names
- [x] Update FEATURE_STATUS.md, status.md, this file; commit `spec 0006: <summary>`

## Validation commands

```bash
python -m pytest code/tests/test_identity.py -q
python code/evaluation/run_eval.py --split dev
```
