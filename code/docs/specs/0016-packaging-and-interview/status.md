# Spec 0016 — packaging-and-interview: status

**Status:** Completed (2026-10-25, overnight run)

## Evidence

```text
$ python code/tools/make_zip.py && python -c "...assert not any('dataset/' in n or n.endswith('.env') ...)"
wrote code.zip: 226 files, ~320 KB; secret scan clean (key patterns + the values of the provider credential env vars)
zip root = contents of code/: .env.example README.md config docs evaluation ghostaudit main.py prompts recon.py
requirements.txt tests tools trace_gold.py; includes evaluation/evaluation_report.md and evaluation/usage_report.md
Clean-room check: unzip into <tmp>/code next to a copy of dataset/ (no model cache):
  python code/main.py --cases sample --offline → 32 rows, validator 0 errors (status 21/32 = the deterministic ablation)
  python -m pytest code/tests -q → 108 passed, 2 skipped (after making test_main independent of a model cache)
```

## Notes

- `code/tools/make_zip.py`: files from `git ls-files code/` only (so untracked caches, runs and `.env` can never ship),
  excluding `.cache/`, `runs/`, `__pycache__`, `dataset/`, `.zip`, `.pyc`; fixed zip timestamps; fails if a required
  file is missing or a key-like string / provider credential value is found. `code.zip` is gitignored and rebuilt on
  demand.
- `code/README.md`: layout (unzip into `code/` next to `dataset/`), architecture table, setup, env vars, run, evaluate,
  ablation flags. `code/docs/INTERVIEW_NOTES.md`: architecture, investigation, remediation planning, case_11
  walkthrough, evaluation numbers, failures fixed, limits.
- Found during the clean-room check: `test_main` assumed every sample reaches the account stage; without cached model
  answers the provisional keyword gate stops 4 samples earlier. The test now checks the account link only for
  non-NOT_APPLICABLE rows (test-only change; pipeline code unchanged since `375604e`).
- Not done by design: no automatic submission. The agent-trace archive is built at wrap-up, separately from code.zip.
