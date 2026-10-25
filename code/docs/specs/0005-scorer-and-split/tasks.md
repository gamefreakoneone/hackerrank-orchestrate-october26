# Spec 0005 — scorer-and-split: tasks

- [ ] score.py
- [ ] split.json
- [ ] run_eval.py
- [ ] tests for scorer on toy inputs
- [ ] baseline snapshot in status.md
- [ ] Update FEATURE_STATUS.md, status.md, this file; commit `spec 0005: <summary>`

## Validation commands

```bash
python code/main.py --cases sample --out runs/sample.csv
python code/evaluation/score.py runs/sample.csv dataset/sample_output.csv --split dev
python -m pytest code/tests/test_score.py -q
```
