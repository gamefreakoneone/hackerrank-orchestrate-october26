# Spec 0005 — scorer-and-split: tasks

- [x] score.py
- [x] split.json
- [x] run_eval.py
- [x] tests for scorer on toy inputs
- [x] baseline snapshot in status.md
- [x] Update FEATURE_STATUS.md, status.md, this file; commit `spec 0005: <summary>`

## Validation commands

```bash
python code/main.py --cases sample --out runs/sample.csv
python code/evaluation/score.py runs/sample.csv dataset/sample_output.csv --split dev
python -m pytest code/tests/test_score.py -q
```
