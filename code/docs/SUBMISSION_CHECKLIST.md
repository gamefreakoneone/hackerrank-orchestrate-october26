# SUBMISSION_CHECKLIST

Source of the requirements: `AGENTS.md` §6.3, §6.7–6.9, `problem_statement.md` (Evaluation, Submission,
Token Usage), `agent_trace_instructions.md`. Official challenge / submission page:
https://www.hackerrank.com/contests/hackerrank-orchestrate-october26/challenges/ghost-data-still-exists

No deadline is configured in the repository; none is assumed. This run prepares artifacts and does **not** submit.

| # | Artifact | Exact path / format | Producing command | Status |
|---|---|---|---|---|
| 1 | Predictions | `<repo>/output.csv`; header `case_id,deletion_status,steps_json`; 518 rows sorted by case number; statuses `COMPLETE/INCOMPLETE/NOT_APPLICABLE`; compact JSON steps | `python code/main.py --cases all --no-cache` (spec 0015) then validator | **Ready (audited pipeline output)**: run `output_candidate_20261025T085130Z`, code `375604e`, sha256 `09c8ecf6…786e3`; 518 rows; INCOMPLETE 461 / COMPLETE 47 / NOT_APPLICABLE 10 |
| 2 | Validator pass on the selected output | exit 0, no errors | `python -c "import sys;sys.path.insert(0,'code');from ghostaudit.validate import cli;cli()"` (spec 0004) | Passes on the selected output: 0 errors, 104 blocker warnings |
| 3 | `code.zip` | zip of `code/`: runnable solution, prompts, config, `README.md`, `evaluation/`; excludes `dataset/`, `.env`, caches, `runs/`, nested archives, secrets | `python code/tools/make_zip.py` (spec 0016) | Built and verified (226 files, secret scan clean, clean-room run + tests pass); gitignored, rebuild before upload |
| 4 | Evaluation report | `code/evaluation/evaluation_report.md` → `evaluation/evaluation_report.md` in the zip: status accuracy, step- and field-level accuracy, sequence accuracy, ≥3 custom cases, failures and improvements | `python code/evaluation/make_reports.py` (spec 0015) | Built from the selected run |
| 5 | Usage report | `code/evaluation/usage_report.md` → `evaluation/usage_report.md`: providers/models, calls, input/output tokens, total and average tokens per request, estimated total and per-request cost, per-model and overall | `python code/evaluation/make_reports.py` from the final run's ledger (spec 0015) | Built from the final cold run's ledger (costs are labelled third-party estimates) |
| 6 | README | `code/README.md`: setup, env vars, run, evaluate | maintained per spec | Final (layout, architecture, setup, env vars, run, evaluate, ablations) |
| 7 | Chat transcript | root `log.txt` (AGENTS.md §2, §5), append-only, exact `tool=`/`model=` per entry | appended every turn / spec | Current: SESSION START, verbatim kickoff, one continuation entry per spec and the wrap-up |
| 8 | Agent trace | `agent-trace.zip` of `agent-trace/` (per-harness subfolders: `claude-code/`, `opencode/`); kept outside `code.zip` | `scripts/save_trace.sh` per checkpoint; `zip -r agent-trace.zip agent-trace` at wrap-up | Exported before every commit; agent-trace.zip built and checked at wrap-up (rebuild after any later session) |
| 9 | Interview notes | `code/docs/INTERVIEW_NOTES.md` | spec 0016 | Written |
| 10 | Consistency | selected run ID, producing commit, output checksum, diagnostics and usage ledger match the reports and `code.zip` | spec 0015/0016 | output.csv ↔ manifest ↔ reports verified (make_reports checks the sha256); code.zip built from the same tree |

## Human steps remaining

1. Confirm the deadline on the challenge page (not configured in the repo).
2. Rebuild `code.zip` (`python code/tools/make_zip.py`) and `agent-trace.zip` (`zip -r agent-trace.zip agent-trace`) from
   the final commit, upload them with root `output.csv` and the `log.txt` transcript, and do the AI interview
   (`code/docs/INTERVIEW_NOTES.md`). Nothing was submitted automatically.
