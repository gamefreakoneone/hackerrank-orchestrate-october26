# Spec 0014 — custom-eval-and-metamorphic: requirements

**Depends on:** 0012, 0013

## Goal

Team-created evaluation cases and metamorphic tests (problem statement requires ≥3 custom cases).

## Requirements / acceptance criteria

- These are **custom and metamorphic validation**, not a holdout: they are designed around known risks and will be
  used to fix the system. Write expected outputs from the rules before running the pipeline on them, and keep a
  record of which cases drove fixes.
- ≥7 synthetic cases under `code/evaluation/cases/` (each: request row, minimal evidence/activity overlay,
  expected output, rationale): historical email + decoy name; post-audit evidence must be ignored; non-deletion
  multilingual request; tombstone + active sync; retained backup with restore blocked; expired retention_until
  (condition FALSE ⇒ `POLICY_UNDEFINED`, INCOMPLETE, no inferred DELETE); repeated request by the same subject with
  different audit_at; ungrounded account (⇒ `ACCOUNT_UNGROUNDED`, never COMPLETE).
- Metamorphic: appending a post-cutoff audit row for the subject leaves that request's output unchanged.
- Overlay runner builds a temp dataset dir = real dataset + overlay files (never edits `dataset/`).
- Metamorphic tests: shuffling CSV row order, adding an unrelated user's records, or moving a file's captured_at past
  audit_at changes output only as expected.

## Out of scope

Anything owned by another spec in `code/docs/FEATURE_STATUS.md`. Hard rules in `CLAUDE.md` apply.
