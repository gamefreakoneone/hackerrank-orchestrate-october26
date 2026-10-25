# Spec 0007 — evidence-parsers: tasks

- [x] sql.py
- [x] json_.py
- [x] logs.py (6 formats + trace grouping)
- [x] text.py
- [x] pdf.py
- [x] index.py + cache
- [x] categories.yaml
- [x] tests per format using real files (small asserts)
- [x] coverage report script `code/tools/evidence_coverage.py`
- [x] Update FEATURE_STATUS.md, status.md, this file; commit `spec 0007: <summary>`

## Validation commands

```bash
python -m pytest code/tests/test_evidence_*.py -q
python code/tools/evidence_coverage.py
python code/evaluation/run_eval.py --split dev
```
