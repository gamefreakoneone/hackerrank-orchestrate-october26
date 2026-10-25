# Spec 0007 — evidence-parsers: tasks

- [ ] sql.py
- [ ] json_.py
- [ ] logs.py (6 formats + trace grouping)
- [ ] text.py
- [ ] pdf.py
- [ ] index.py + cache
- [ ] categories.yaml
- [ ] tests per format using real files (small asserts)
- [ ] coverage report script `code/tools/evidence_coverage.py`
- [ ] Update FEATURE_STATUS.md, status.md, this file; commit `spec 0007: <summary>`

## Validation commands

```bash
python -m pytest code/tests/test_evidence_*.py -q
python code/tools/evidence_coverage.py
python code/evaluation/run_eval.py --split dev
```
