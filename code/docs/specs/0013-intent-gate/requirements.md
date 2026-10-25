# Spec 0013 — intent-gate: requirements

**Depends on:** 0008, 0012

## Goal

Decide whether request_text authorizes deletion (multilingual).

## Requirements / acceptance criteria

- Jev choice over `DELETION / ACCESS / CORRECTION / EXPORT / OPT_OUT / OTHER`; accept if confidence ≥
  `JEV_CONFIDENCE_THRESHOLD` and it agrees with the keyword check; otherwise Azure adjudicates (structured enum).
- Keyword check: multilingual deletion lexicon (en, es, fr, de, pt, it, ja, …) in `code/config/intent_lexicon.yaml`.
- Non-deletion ⇒ NOT_APPLICABLE with `[]`; no other pipeline step runs.
- Report CLASSIFY_REQUEST disagreements (cross-check only, never decisive).
- All 32 samples must classify as DELETION (gold has 0 NOT_APPLICABLE).

## Out of scope

Anything owned by another spec in `code/docs/FEATURE_STATUS.md`. Hard rules in `CLAUDE.md` apply.
