# Spec 0011 — policy-obligations: tasks

- [ ] policy.py
- [ ] obligations.py
- [ ] Jev category fallback hook
- [ ] tests for each template + tombstone
- [ ] obligation report on dev split
- [ ] Update FEATURE_STATUS.md, status.md, this file; commit `spec 0011: <summary>`

## Validation commands

```bash
python -m pytest code/tests/test_policy.py code/tests/test_obligations.py -q
python code/evaluation/run_eval.py --split dev
```
