# Spec 0012 — planner-and-evidence: tasks

- [x] planner.py
- [x] cite.py — not a separate module: the citation is the obligation proof computed by timeline.py (same rule; see status.md)
- [x] pipeline.py + main wiring
- [x] end-to-end tests on 5 dev cases
- [x] error analysis on dev; fixes logged in status.md
- [x] Update FEATURE_STATUS.md, status.md, this file; commit `spec 0012: <summary>`

## Validation commands

```bash
python code/main.py --cases sample --out runs/sample.csv
python code/evaluation/score.py runs/sample.csv dataset/sample_output.csv --split dev
python -m pytest code/tests -q
```
