# Spec 0013 — intent-gate: status

**Status:** Completed (2026-10-25, overnight run)

## Evidence

```text
$ python -m pytest code/tests/test_intent.py -q
5 passed, 1 skipped (decision table with fake Jev/Azure transports; offline keyword path)
$ RUN_LIVE=1 python -m pytest code/tests/test_intent.py -q -k live
1 passed: all 32 samples → DELETION; 6 synthetic non-deletion requests (access, correction, export, opt-out,
Spanish access, French correction) → their labels
$ python code/main.py --cases all --out runs/all.csv && python code/tools/intent_report.py
518 requests: DELETION 508 (jev); non-deletion 10 = CORRECTION 3 (jev), OTHER 2 (jev), EXPORT 1 (jev),
OPT_OUT 1 (jev) + 1 (azure), ACCESS 2 (azure); keyword disagreements 3 (case_534/539/542: negated deletion
words, resolved by Azure to OPT_OUT/ACCESS/ACCESS); validator 0 errors; statuses INCOMPLETE 461, COMPLETE 47,
NOT_APPLICABLE 10
Samples: 32/32 DELETION (28 jev, 4 azure: case_06, 15, 25, 26 — audit/verification wording without a deletion verb)
$ python code/evaluation/run_eval.py --split dev     (same numbers as below)
```

Model usage of the intent probes and first full pass: ≈ 550 Jev calls (~440 input / ~50 output tokens each) and 7
Azure adjudications; later passes are fully cached (runs/usage_all_*.jsonl: 535 cached calls, 0 new).
CLASSIFY_REQUEST cross-check: the dataset has 10 CLASSIFY_REQUEST "non-deletion" activities and the gate returns
exactly 10 non-deletion decisions; among the 508 DELETION cases none has a CLASSIFY_REQUEST on its grounded account
(0 disagreements). The activities name accounts, not requests, so the check is only possible through a grounded link.

## Scorer snapshot (dev)

| | Status acc | Account linkage | Step F1 | Seq exact |
|---|---|---|---|---|
| before (0012, gate not applied) | 0.750 | 7/20 | 0.904 | 0.250 |
| after | 0.750 | 7/20 | 0.904 | 0.250 |

## Notes

- `intent.py` decision table (code decides): Jev Choice over DELETION/ACCESS/CORRECTION/EXPORT/OPT_OUT/OTHER;
  accepted when the top label's probability ≥ `JEV_CONFIDENCE_THRESHOLD` (0.8) **and** it agrees with the keyword
  check; otherwise Azure adjudicates with a structured enum; Azure failure → Jev label marked `jev_unconfirmed`; no
  model available → keyword-only, marked `keyword_provisional` in diagnostics. Non-deletion ⇒ NOT_APPLICABLE with `[]`
  and no other pipeline step.
- `config/intent_lexicon.yaml`: multilingual deletion stems (en, es, pt, fr, de, it, nl, ja, ko, zh). Cross-check only:
  negated requests contain the same words.
- Offline limitation (recorded for the 0015 ablation): keyword-only misses deletion-audit wording (case_06/15/25/26
  style) and would return NOT_APPLICABLE for them.
