# Spec 0010 — discovery-and-state: tasks

- [ ] discovery.py
- [ ] account_link.py
- [ ] timeline.py
- [ ] discovery_report.py
- [ ] tests: case_05 replica drift, case_06 decoy, case_15 trace grouping, case_17 restore risk, full_table absence (case_01)
- [ ] Update FEATURE_STATUS.md, status.md, this file; commit `spec 0010: <summary>`

## Validation commands

```bash
python -m pytest code/tests/test_discovery.py code/tests/test_timeline.py -q
python code/tools/discovery_report.py --split dev
python code/evaluation/run_eval.py --split dev
```
