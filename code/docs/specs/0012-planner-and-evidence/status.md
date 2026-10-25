# Spec 0012 — planner-and-evidence: status

**Status:** Completed (2026-10-25, overnight run)

## Evidence

```text
$ python code/main.py --cases sample --out runs/sample.csv
wrote 32 rows; validation: 0 errors, 9 warnings (INCOMPLETE without findings, each with a blocker flag)
$ python code/evaluation/score.py runs/sample.csv dataset/sample_output.csv --split dev
status 0.750 (15/20); linkage 7/20 (precision 1.000); step P/R/F1 1.000/0.824/0.904 (103 matched, 103 pred, 125 gold);
field acc on matched: phase 1.000, state 1.000, evidence_id 0.903, step_no 0.728; sequence exact 0.250 (5/20); LCS 0.746
--split holdout: status 8/12; F1 0.889; sequence exact 4/12
--split all: status 23/32 (0.719); F1 0.898 (159/161 pred, 193 gold); evidence_id 0.899; sequence exact 9/32; LCS 0.724
$ python -m pytest code/tests -q
99 passed, 1 skipped
Development full pass (runs/dev_all.csv, not the submission): 518 rows, validator 0 errors / 113 blocker warnings;
47 COMPLETE, 471 INCOMPLETE; flags ACCOUNT_UNGROUNDED 351, CONDITION_DEFAULTED 339, EMPTY_OBLIGATIONS 10, UNKNOWN_STATE 2.
```

## Scorer snapshot (dev)

| | Status acc | Account linkage | Step F1 | Seq exact |
|---|---|---|---|---|
| before (0011, stub pipeline) | 0.000 | not measured | 0.000 | 0.000 |
| after | 0.750 | 7/20 correct, 0 wrong, 13 ungrounded | 0.904 | 0.250 |

Status on all samples (23/32) equals the conditional upper bound recorded in TECHNICAL_DESIGN §3.5: all 9 status misses
are gold-COMPLETE cases that carry ACCOUNT_UNGROUNDED (case_01, 02, 04, 21, 25–28, 31).

## Error analysis (all 32)

Every remaining step difference falls into one of three documented gaps; none is a planner or citation error:
1. Ungrounded accounts (20 cases): no account steps; for the 9 gold-COMPLETE ones the status becomes INCOMPLETE, so
   their verification steps carry `""` instead of gold's citation (all 11 evidence_id differences on matched steps).
2. Anonymized analytics without a grounded link (case_03, 04, 21, 25–28): VERIFY_RECORD_ANONYMIZED missing.
3. Retained audit records with no eligible evidence (7 cases): VERIFY_RECORD_PRESENT missing.
Extra steps (2): case_17 historical account_6523 (accepted by design) and tombstone_17 (catalog-linked, Jev category
fallback → ACCOUNT_TOMBSTONE, absent from the snapshots that hold its collection → verify REDACTED).
Where the account is grounded, every case's plan equals gold exactly (9/9; 5 asserted in test_pipeline_e2e.py).

Fix made during this spec: generic `customer_data_*` snapshots now claim coverage only for collections that some table
of the same file holds (previously every known collection, even if absent from the whole file); state report and
scores unchanged (104/111 states, 75/75 proofs).

## Notes

- `planner.py`: status = no blocker ∧ ≥1 obligation ∧ every obligation satisfied with proof; INCOMPLETE ⇒ finding
  (cited) + remediation for unsatisfied obligations with known state, verification `""` for all; COMPLETE ⇒
  verification citing the proof; canonical order via `serialize.canonical`.
- No `cite.py`: the citation rule (latest establishing file → snapshot omission per §5 Q2 → state-check activity) is
  exactly how `timeline.state_at` establishes each state, so the obligation's `proof` is the citation. A second module
  would duplicate it. Audit-id citations were never needed (0 in samples and in the development full pass).
- `pipeline.run_case` + `diagnostics_record`; `main.py` builds the ledger (with cached PNG rows), runs every case, writes
  `<out>.diagnostics.jsonl`, a run manifest (`runs/<run_id>.manifest.json`: git revision, args, output sha256, usage),
  the usage ledger `runs/usage_<run_id>.jsonl`, and validates with diagnostics. The intent gate is not applied before
  spec 0013 (diagnostics say `"not evaluated before spec 0013"`).
