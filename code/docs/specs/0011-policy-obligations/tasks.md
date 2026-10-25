# Spec 0011 — policy-obligations: tasks

- [x] policy.py
- [x] obligations.py
- [x] Jev category fallback hook
- [x] tests for each template + tombstone
- [x] obligation report on dev split
- [x] Update FEATURE_STATUS.md, status.md, this file; commit `spec 0011: <summary>`

## Validation commands

```bash
python -m pytest code/tests/test_policy.py code/tests/test_obligations.py -q
python code/evaluation/run_eval.py --split dev
```
