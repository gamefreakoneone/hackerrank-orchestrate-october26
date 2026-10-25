# Spec 0002 — dataset-recon: tasks

- [x] recon.py + DATA_NOTES.md
- [x] trace_gold.py + GOLD_TRACE.md
- [x] Phase-0 scripts p0_q1..q5
- [x] Answers in TECHNICAL_DESIGN §5
- [x] Phase-0b corrections after Codex review (cutoff-safe exact baselines)
- [x] Update FEATURE_STATUS.md, status.md, this file; commit `spec 0002: <summary>`

## Validation commands

```bash
python code/recon.py
python code/trace_gold.py
cd code/tools && python p0_q2_evidence_selection.py && python p0_q2b_coverage.py | head -30 && python p0_q3_discovery.py | tail -1 && python p0_q3c_account_link.py | tail -1 && python p0_q1_q5_categories.py
```
