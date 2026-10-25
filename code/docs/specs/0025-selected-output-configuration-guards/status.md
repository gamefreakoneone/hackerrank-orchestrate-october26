# Spec 0025 — Selected-output configuration guards: status

**Status:** Not started
**Depends on:** completed and remotely published 0024
**Working/push branch:** `claude/specs-0017-0021-5s3kpe`
**Audited baseline:** `88a357ea152601aeca3ce5cc98e0fd764597b1c6`
**Implementation/publication:** not started.

## Evidence available before implementation

The baseline parser/selected-output guard accepted sample, trust-claims and ranked-account modes targeting root
output.csv. No actual overwrite was performed by the audit. The existing --case rejection worked.

## Scorer snapshot

| When / split | Revision / configuration | Status accuracy | Account linkage | Step F1 | Sequence exact |
|---|---|---|---|---|---|
| Before / dev | not measured; planned offline/no-cache after 0024 | not measured | not measured | not measured | not measured |
| After / dev | not measured; same configuration required | not measured | not measured | not measured | not measured |

## Checks and publication

- Isolated CLI publication/refusal tests: not run for this spec.
- Full offline suite / clean-room checks: not measured by this correction pass.
- Corrected default release generation: not authorized or run; preserved release remains at b90914b.
- Implementation SHA, remote verification and release readiness: record separately after execution.
