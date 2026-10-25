# Spec 0013 — intent-gate: tasks

- [x] intent.py + lexicon
- [x] Jev question phrasing per typesafe skill
- [x] Azure fallback
- [x] tests: 32 samples DELETION, 6 synthetic non-deletion (access, correction, export, opt-out, multilingual)
- [x] disagreement report on all 518
- [x] Update FEATURE_STATUS.md, status.md, this file; commit `spec 0013: <summary>`

## Validation commands

```bash
python -m pytest code/tests/test_intent.py -q
python code/main.py --cases all --out runs/all.csv && python code/tools/intent_report.py
python code/evaluation/run_eval.py --split dev
```
