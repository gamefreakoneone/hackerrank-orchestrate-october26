# Spec 0005 — scorer-and-split: requirements

**Depends on:** 0004

## Goal

Grader-replica scorer, frozen dev/holdout split, baseline numbers.

## Requirements / acceptance criteria

- `code/evaluation/score.py PRED GOLD [--split dev|holdout|all]` prints and returns: status accuracy;
  step precision/recall/F1 on keys `(operation, system_id, resource_id)`; field accuracy on matched steps
  (phase, state, evidence_id, step_no); sequence exact-match rate; mean normalized LCS over step keys; per-case table.
- `code/evaluation/split.json`: 20 dev / 12 regression-holdout case_ids, stratified by gold status, fixed seed,
  committed once and never regenerated. **All 32 samples were inspected in Phase 0 and shaped design decisions**, so
  neither split is untouched validation: both are regression sets. Reports must say so. Spec 0014's cases are
  custom and metamorphic validation, also not a holdout; no untouched holdout exists.
- `code/evaluation/run_eval.py`: runs `main.py --cases sample --out runs/sample.csv` then scores; writes
  `runs/score_<timestamp>.md`.
- Baseline recorded (stub output).

## Out of scope

Anything owned by another spec in `code/docs/FEATURE_STATUS.md`. Hard rules in `CLAUDE.md` apply.
