# SUBMISSION_CHECKLIST

Source of the requirements: `AGENTS.md` §6.3, §6.7–6.9, `problem_statement.md` (Evaluation, Submission,
Token Usage), `agent_trace_instructions.md`. Official challenge / submission page:
https://www.hackerrank.com/contests/hackerrank-orchestrate-october26/challenges/ghost-data-still-exists

No deadline is configured in the repository; none is assumed. This run prepares artifacts and does **not** submit.

| # | Artifact | Exact path / format | Producing command | Status |
|---|---|---|---|---|
| 1 | Predictions | `<repo>/output.csv`; header `case_id,deletion_status,steps_json`; 518 rows sorted by case number; statuses `COMPLETE/INCOMPLETE/NOT_APPLICABLE`; compact JSON steps | `python code/main.py --cases all --no-cache` (spec 0015) then validator | Not ready — only a **format-only baseline** (all NOT_APPLICABLE, spec 0001) exists, untracked; not an audited result |
| 2 | Validator pass on the selected output | exit 0, no errors | `python -c "import sys;sys.path.insert(0,'code');from ghostaudit.validate import cli;cli()"` (spec 0004) | Not built |
| 3 | `code.zip` | zip of `code/`: runnable solution, prompts, config, `README.md`, `evaluation/`; excludes `dataset/`, `.env`, caches, `runs/`, nested archives, secrets | `python code/tools/make_zip.py` (spec 0016) | Not built |
| 4 | Evaluation report | `code/evaluation/evaluation_report.md` → `evaluation/evaluation_report.md` in the zip: status accuracy, step- and field-level accuracy, sequence accuracy, ≥3 custom cases, failures and improvements | `python code/evaluation/make_reports.py` (spec 0015) | Not built |
| 5 | Usage report | `code/evaluation/usage_report.md` → `evaluation/usage_report.md`: providers/models, calls, input/output tokens, total and average tokens per request, estimated total and per-request cost, per-model and overall | `python code/evaluation/make_reports.py` from the final run's ledger (spec 0015) | Not built |
| 6 | README | `code/README.md`: setup, env vars, run, evaluate | maintained per spec | Skeleton (spec 0001) |
| 7 | Chat transcript | root `log.txt` (AGENTS.md §2, §5), append-only, exact `tool=`/`model=` per entry | appended every turn / spec | Ongoing |
| 8 | Agent trace | `agent-trace.zip` of `agent-trace/` (per-harness subfolders: `claude-code/`, `opencode/`); kept outside `code.zip` | `scripts/save_trace.sh` per checkpoint; `zip -r agent-trace.zip agent-trace` at wrap-up | Checkpoints ongoing; zip not built |
| 9 | Interview notes | `code/docs/INTERVIEW_NOTES.md` | spec 0016 | Not built |
| 10 | Consistency | selected run ID, producing commit, output checksum, diagnostics and usage ledger match the reports and `code.zip` | spec 0015/0016 | Not applicable yet |
