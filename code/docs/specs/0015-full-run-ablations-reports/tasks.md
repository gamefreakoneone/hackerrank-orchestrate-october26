# Spec 0015 — full-run-ablations-reports: tasks

- [x] ablation flags
- [x] cold full run
- [x] make_reports.py
- [x] evaluation_report.md
- [x] usage_report.md
- [x] Update FEATURE_STATUS.md, status.md, this file; commit `spec 0015: <summary>`

## Validation commands

```bash
python code/main.py --cases all --no-cache
python -c "import sys;sys.path.insert(0,'code');from ghostaudit.validate import cli;cli()"
python code/evaluation/run_eval.py --split all
python code/evaluation/make_reports.py
```
