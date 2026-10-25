# SUBMISSION_CHECKLIST

> **Corrected release (specs 0017–0021):** the rows below describe the corrected selected run
> `0021_candidate_20261025T104010Z` (producing code `b90914b`), published by `code/tools/finalize_run.py` after the
> candidate, its diagnostics, usage ledger and the same-revision evaluation inputs validated together. The overnight
> run (`375604e`, sha256 `09c8ecf6…`) is the previous release, kept in Git history.

Source of the requirements: `AGENTS.md` §6.3, §6.7–6.9, `problem_statement.md` (Evaluation, Submission,
Token Usage), `agent_trace_instructions.md`. Official challenge / submission page:
https://www.hackerrank.com/contests/hackerrank-orchestrate-october26/challenges/ghost-data-still-exists

No deadline is configured in the repository; none is assumed. This run prepares artifacts and does **not** submit.

| # | Artifact | Exact path / format | Producing command | Status |
|---|---|---|---|---|
| 1 | Predictions | `<repo>/output.csv`; header `case_id,deletion_status,steps_json`; 518 rows sorted by case number; statuses `COMPLETE/INCOMPLETE/NOT_APPLICABLE`; compact JSON steps | `python code/main.py --cases all --no-cache --out runs/corrective/0021_candidate.csv --run-manifest-output …` then `code/tools/finalize_run.py` (spec 0021) | **Ready (corrected pipeline output)**: run `0021_candidate_20261025T104010Z`, code `b90914b`, sha256 `81b31784…0ecb`; 518 rows; INCOMPLETE 459 / COMPLETE 49 / NOT_APPLICABLE 10 |
| 2 | Validator pass on the selected output | exit 0, no errors | `python -c "import sys;sys.path.insert(0,'code');from ghostaudit.validate import cli;cli()" output.csv --diagnostics code/evaluation/final_run/diagnostics.jsonl` (spec 0004; diagnostics argument added by 0020) | Passes on the selected output: 0 errors, 105 blocker warnings, each an INCOMPLETE case whose blocker flag explains the missing finding (without the diagnostics these are errors) |
| 3 | `code.zip` | zip of `code/`: runnable solution, prompts, config, `README.md`, `evaluation/`; excludes `dataset/`, `.env`, caches, `runs/`, nested archives, secrets | `python code/tools/make_zip.py` (spec 0016) | Built from the corrected tree: 271 files, secret scan clean; `test_packaging_integrity.py` rebuilds it and, in a clean room (archive + dataset + output.csv only), reproduces both reports byte-identically and runs an offline sample pass. Gitignored: rebuild before upload |
| 4 | Evaluation report | `code/evaluation/evaluation_report.md` → `evaluation/evaluation_report.md` in the zip: status accuracy, step- and field-level accuracy, sequence accuracy, ≥3 custom cases, failures and improvements | `python code/evaluation/capture_inputs.py` then `python code/evaluation/make_reports.py` (specs 0015, 0020: hashed inputs, no model calls) | Built by `finalize_run.py` from the selected run and the same-revision bundle `code/evaluation/corrective_run/`; `make_reports.py` rebuilds it byte-identically offline |
| 5 | Usage report | `code/evaluation/usage_report.md` → `evaluation/usage_report.md`: providers/models, calls, input/output tokens, total and average tokens per request, estimated total and per-request cost, per-model and overall | `python code/evaluation/make_reports.py` from the final run's ledger (specs 0015, 0021) | Built from the corrected cold run's ledger: 535 calls, 273,276 input / 92,347 output tokens, est. $0.24 (estimated, unverified third-party prices) |
| 6 | README | `code/README.md`: setup, env vars, run, evaluate | maintained per spec | Final (layout, architecture, setup, env vars, run, evaluate, ablations) |
| 7 | Chat transcript | root `log.txt` (AGENTS.md §2, §5), append-only, exact `tool=`/`model=` per entry | appended every turn / spec | Current: includes the corrective session's SESSION START and one entry per spec 0017–0021 |
| 8 | Agent trace | `agent-trace.zip` of `agent-trace/` (per-harness subfolders: `claude-code/`, `opencode/`); kept outside `code.zip` | `scripts/save_trace.sh` per checkpoint; `zip -r agent-trace.zip agent-trace` at wrap-up | Exported before every commit; agent-trace.zip built and checked at wrap-up (rebuild after any later session) |
| 9 | Interview notes | `code/docs/INTERVIEW_NOTES.md` | spec 0016 | Updated with the corrective pass and corrected numbers |
| 10 | Consistency | selected run ID, producing commit, output checksum, diagnostics and usage ledger match the reports and `code.zip` | spec 0015/0016 | output.csv ↔ final_run manifest (output/diagnostics/ledger sha256) ↔ evaluation inputs (same revision `b90914b`) ↔ reports verified by `finalize_run.py`, `make_reports.py` and `test_packaging_integrity.py`; `.gitattributes` keeps the hashed files byte-exact on CRLF checkouts |

## Human steps remaining

1. Confirm the deadline on the challenge page (not configured in the repo).
2. Rebuild `code.zip` (`python code/tools/make_zip.py`) and `agent-trace.zip` (`zip -r agent-trace.zip agent-trace`) from
   the final commit, upload them with root `output.csv` and the `log.txt` transcript, and do the AI interview
   (`code/docs/INTERVIEW_NOTES.md`). Nothing was submitted automatically.
