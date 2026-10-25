# Spec 0016 — packaging-and-interview: requirements

**Depends on:** 0015

## Goal

Submission artifacts and interview preparation.

## Requirements / acceptance criteria

- `code/tools/make_zip.py` builds `code.zip` from `code/` excluding `.env`, `.cache/`, `runs/`, `__pycache__`,
  nested archives, and anything under `dataset/`; asserts `evaluation/evaluation_report.md` and
  `evaluation/usage_report.md` are present; scans for key-like strings and fails if found.
- `code/README.md` final: setup, env vars, run, evaluate, architecture summary.
- `code/docs/INTERVIEW_NOTES.md`: architecture, one walkthrough case end to end, investigation approach,
  remediation planning, evaluation numbers, failures fixed.

## Out of scope

Anything owned by another spec in `code/docs/FEATURE_STATUS.md`. Hard rules in `CLAUDE.md` apply.
