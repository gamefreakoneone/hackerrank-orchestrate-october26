# Spec 0015 — full-run-ablations-reports: status

**Status:** Completed (2026-10-25, overnight run)

## Selected final run

| Item | Value |
|---|---|
| Run ID | `output_candidate_20261025T085130Z` |
| Producing code revision | `375604e` (code freeze commit, made before the run) |
| Command | `python code/main.py --cases all --no-cache --out runs/final/output_candidate.csv` (cold: no cache reads) |
| Output | promoted to root `output.csv` after validation; sha256 `09c8ecf6781e295799866b3e875c21f456de240f8d0b31f4b960a8f59ac786e3` (byte-identical) |
| Validator | 0 errors, 104 warnings (INCOMPLETE without findings / `[]`, each with a blocker flag), 0 activity/audit citations |
| Status distribution | INCOMPLETE 461, COMPLETE 47, NOT_APPLICABLE 10 |
| Diagnostics / ledger / manifest | `code/evaluation/final_run/{diagnostics.jsonl, usage_ledger.jsonl, manifest.json}` (copies of the runs/ files) |
| Model usage | 535 real calls, 0 cached: Jev 521 (518 intent + 3 category fallback), Gemini 11 (PNG), Azure 3 (intent adjudication); 273,276 input + 88,704 output tokens; estimated $0.2266 total, $0.00044 per request (third-party price estimates) |
| Determinism | identical (all 518 rows) to the earlier cached development pass `runs/all.csv` |

## Evidence

```text
$ python code/main.py --cases all --no-cache --out runs/final/output_candidate.csv     # 8 min wall clock
validation: 0 errors, 104 warnings, 0 activity citations, 0 audit citations
$ python -c "...validate import cli;cli()" --diagnostics runs/final/output_candidate.diagnostics.jsonl   # root output.csv
validation: 0 errors, 104 warnings
$ python code/evaluation/run_eval.py --split all   (runs/sample.csv on the frozen code)
status 23/32, linkage 12/32 (0 wrong), F1 0.898, sequence exact 9/32
$ python code/evaluation/run_custom.py             → 9/9 requests fully pass
$ python code/evaluation/make_reports.py          → code/evaluation/evaluation_report.md, usage_report.md
$ python -m pytest code/tests -q                   → 108 passed, 2 skipped
```

## Ablations (samples, all 32; full-dataset status counts in the evaluation report)

| Configuration | Status | Linkage | Step F1 | Seq exact |
|---|---|---|---|---|
| default | 23/32 | 12/32 | 0.898 | 9/32 |
| deterministic-only (`--offline --no-cache`) | 21/32 | 10/32 (4 cases gated out as NOT_APPLICABLE by the provisional keyword check) | 0.855 | 7/32 |
| no historical identifiers | 22/32 | 12/32 | 0.889 | 8/32 |
| trust activity claims | 23/32 | 12/32 | 0.898 | 9/32 (2 proofs switch to claim activity ids; later evidence dominates) |
| ranked guessed accounts (INCOMPLETE only) | 23/32 | 12/32 grounded; guesses 8 right / 12 wrong | 0.893 (P 0.923, R 0.865) | 13/32 |

Full dataset: deterministic-only 48/463/7 (COMPLETE/INCOMPLETE/NOT_APPLICABLE: 3 non-deletion requests slip through the
keyword path), no-history 38/470/10, trust-claims and ranked identical to default in status counts.

## Scorer snapshot (dev)

| | Status acc | Account linkage | Step F1 | Seq exact |
|---|---|---|---|---|
| before (0014) | 0.750 | 7/20 | 0.904 | 0.250 |
| after (final code) | 0.750 | 7/20 | 0.904 | 0.250 |

## Notes

- Ablation flags (`--ablate no-history|trust-claims`, `--ungrounded-account-steps ranked`) are evaluation-only; the
  ranked ablation keeps ACCOUNT_UNGROUNDED, so a guessed account can never produce COMPLETE.
- Prices: no official price page was found for jev-1.14.0, gpt-6-luna or gemini-3.8-flash; `code/config/pricing.yaml`
  records third-party estimates with their sources and the usage report labels all costs as estimates.
- Only report code (`make_reports.py`) changed after the code freeze; the pipeline that produced `output.csv` is `375604e`.
