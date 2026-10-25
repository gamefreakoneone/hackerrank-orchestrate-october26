# Spec 0022 — Observation-time cutoffs: status

**Status:** Not started
**Working/push branch:** `claude/specs-0017-0021-5s3kpe`
**Audited baseline:** `88a357ea152601aeca3ce5cc98e0fd764597b1c6`
**Implementation/publication:** not started; this folder is a specification, not a fix.

## Evidence available before implementation

Review B1 reproduced future FOUND observations affecting two saved rows. The component-only counterfactual changed
their account obligations to ABSENT and their saved-obligation plans to COMPLETE. Full corrected inference has not
been run. See `../../reviews/0002-corrective-pass-review.md` for the exact scope and timestamps.

## Scorer snapshot

| When / split | Revision / configuration | Status accuracy | Account linkage | Step F1 | Sequence exact |
|---|---|---|---|---|---|
| Before / dev | not measured; planned offline/no-cache | not measured | not measured | not measured | not measured |
| After / dev | not measured; same configuration required | not measured | not measured | not measured | not measured |

The preserved default sample bundle scores 23/32, linkage 12/32, F1 0.895775 and exact 9/32 over all samples.
Those are historical saved-bundle metrics, not the before/after rows above.

## Checks and publication

- Focused tests: not run for this spec.
- Affected-case assessment under corrected inference: not measured.
- Output/diagnostics/report changes: none authorized by specification creation.
- Commit SHA and verified remote: fill after actual implementation/publication; never invent a self-SHA.
