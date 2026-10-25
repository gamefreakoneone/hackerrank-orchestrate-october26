# Spec 0003 — data-contracts-loaders: tasks

- [x] models.py with enums/tables
- [x] loaders.py
- [x] tests: row counts (518/32/850/306/4011/15/94), tz-aware, OP tables complete
- [x] Update FEATURE_STATUS.md, status.md, this file; commit `spec 0003: <summary>`

## Validation commands

```bash
python -m pytest code/tests/test_loaders.py code/tests/test_models.py -q
```
