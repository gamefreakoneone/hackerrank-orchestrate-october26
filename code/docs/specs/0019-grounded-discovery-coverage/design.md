# Spec 0019 — Grounded discovery coverage: design

Start from `tools/discovery_report.py` and the existing ledger/account-link diagnostics. Keep scoring separate
from inference: sample answers may identify misses for investigation, never supply the pipeline's targets.

1. Build a per-miss investigation table from the measured sample output and participant-visible evidence:
   case/resource, eligible source checked, missing link/parser fact, conclusion and proposed general rule if any.
2. Inspect exact identifiers, table/collection scope, trace grouping and explicit `source_resource_id` or
   equivalent relationships actually present in records. A populated profile may link an account; a null
   profile/404 proves state only after independent linkage. Do not reinterpret abbreviated tool previews.
3. If a parser dropped a supported identifier/edge, make the smallest local correction and show its provenance.
   If evidence is absent or ambiguous, document it rather than restoring workflow guesses as proof.
4. Report current-account precision/coverage separately from historical-account coverage and other resources.
   Include the extra-resource count and before/after per-case changes, not just the best aggregate score.
5. Preserve the investigation as `code/docs/DISCOVERY_GAP_REVIEW.md` (planned). Existing tools may emit a small
   machine-readable result for later report rebuilding if needed; reuse the existing scorer conventions.

Bound the investigation to the supplied sources and observed misses. Cache/parser availability must be recorded:
`discovery_report.py` uses cached vision observations, so an empty image cache is not an equivalent live baseline.
Use existing sample runs to populate permitted caches rather than launching a fresh 518-case job for each idea.

## Planned verification

Add `code/tests/test_grounded_discovery_regressions.py` only for supported rules or confirmed existing guards:
unrelated same-name/partial-identifier decoys, post-cutoff links, repeated requests with independent cutoffs,
historical grounded accounts, and a null-profile lookup without ownership information. An investigation-only
completion must still demonstrate the existing no-guess/cutoff guards and preserve a reproducible gap table.
