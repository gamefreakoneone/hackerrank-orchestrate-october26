# Spec 0013 — intent-gate: tasks

- [ ] intent.py + lexicon
- [ ] Jev question phrasing per typesafe skill
- [ ] Azure fallback
- [ ] tests: 32 samples DELETION, 6 synthetic non-deletion (access, correction, export, opt-out, multilingual)
- [ ] disagreement report on all 518
- [ ] Update FEATURE_STATUS.md, status.md, this file; commit `spec 0013: <summary>`

## Validation commands

```bash
python -m pytest code/tests/test_intent.py -q
python code/main.py --cases all --out runs/all.csv && python code/tools/intent_report.py
python code/evaluation/run_eval.py --split dev
```
