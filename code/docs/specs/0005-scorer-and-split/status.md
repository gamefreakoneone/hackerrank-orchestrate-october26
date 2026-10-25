# Spec 0005 — scorer-and-split: status

**Status:** Completed (2026-10-25, overnight run)

## Evidence

```text
$ python code/main.py --cases sample --out runs/sample.csv
validation: 0 errors, 0 warnings, 0 activity citations, 0 audit citations
$ python code/evaluation/score.py runs/sample.csv dataset/sample_output.csv --split dev
Status accuracy 0.000 (0/20); step P/R/F1 0/0/0 (0 pred, 125 gold); sequence exact 0/20; LCS 0.000;
account linkage not_measured 20 (stub writes no diagnostics)
$ python -m pytest code/tests/test_score.py -q
3 passed
$ python code/evaluation/run_eval.py --split all     # report runs/score_20261025T080040Z_all.md
Status accuracy 0/32; F1 0.000 (193 gold steps); sequence exact 0/32
```

## Scorer snapshot (format-only baseline: all NOT_APPLICABLE, `[]`)

| Split | Status acc | Account linkage | Step F1 | Seq exact | Mean LCS |
|---|---|---|---|---|---|
| dev (20) | 0.000 | not measured | 0.000 | 0.000 | 0.000 |
| holdout (12) | 0.000 | not measured | 0.000 | 0.000 | 0.000 |
| all (32) | 0.000 | not measured | 0.000 | 0.000 | 0.000 |

## Notes

- `split.json`: seed 20261025, sorted case_ids shuffled within each gold status, `floor(2/3)` per stratum → dev 20
  (6 COMPLETE + 14 INCOMPLETE), holdout 12 (4 + 8). Frozen; both are inspected regression sets.
- Matching: step keys `(operation, system_id, resource_id)` are unique per case (validator rule), so the multiset
  match is a set intersection; field accuracy over matched pairs (phase, state, evidence_id, step_no); sequence exact
  = parsed step lists equal; LCS over ordered keys / max length (both empty → 1.0).
- Account linkage (separate metric): per case with a gold account_service step, `correct` if the diagnostics'
  `account_link.current` is a gold account, `wrong` if grounded but different, `ungrounded`, or `not_measured` without
  diagnostics. Diagnostics default path: `<pred>.diagnostics.jsonl` (e.g. `runs/sample.diagnostics.jsonl`).
- Flag counts for every TECHNICAL_DESIGN §3.5 flag are reported per run.
- Removed the empty placeholder `code/evaluation/main.py` (superseded by `score.py` / `run_eval.py`).
