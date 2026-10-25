# Spec 0012 — planner-and-evidence: tasks

- [ ] planner.py
- [ ] cite.py
- [ ] pipeline.py + main wiring
- [ ] end-to-end tests on 5 dev cases
- [ ] error analysis on dev; fixes logged in status.md
- [ ] Update FEATURE_STATUS.md, status.md, this file; commit `spec 0012: <summary>`

## Validation commands

```bash
python code/main.py --cases sample --out runs/sample.csv
python code/evaluation/score.py runs/sample.csv dataset/sample_output.csv --split dev
python -m pytest code/tests -q
```
