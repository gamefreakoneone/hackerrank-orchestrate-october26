# Spec 0022 — Observation-time cutoffs: design

## Owned behavior

Start with `ghostaudit/evidence/index.py:eligible`, `timeline.py:observation_time` / `coverage_time`, and the SQL,
JSON and log parsers. Inspect their actual callers in discovery, account_link, pipeline and policy. Read the
identity and PNG filtering paths as well: pre-cutoff decisions must not depend on a post-cutoff identity universe.
This last inspection is a guard requirement, not a claim that a PNG caused either reproduced output error.

1. Inventory where each parser obtains a state-observation time. SQL uses the snapshot header; JSON distinguishes
   observation/read events from business timestamps; logs retain the timing of establishing lines. Retention dates
   and record creation dates remain fields with their own meanings.
2. Define a shared eligibility rule with availability and meaningful observation time. Use descriptive names such
   as `state_observed_at` / `available_at` if the existing names need clarification. Missing observation time may use
   capture time only where the source actually establishes state at capture; document the fallback.
3. Remove backward clipping of future assertions. A timestamp inconsistent with capture time must stay visible
   in diagnostics and cannot prove state before its asserted time. Decide whether to exclude an inconsistent fact
   entirely or admit it only once both bounds pass, based on source semantics; never silently backdate it.
4. Apply the rule to all influence paths, not only state_at. Mixed-time log groups and JSON bundles need enough
   provenance to prevent later identifiers or subject lists contaminating an earlier observation. Prefer the
   smallest parser/record-boundary change over a second temporal engine.
5. Treat coverage conservatively: omitting filtered future records does not make a partial collection a complete
   absence snapshot. A future snapshot cannot prove earlier absence; eligible complete snapshots retain their scope.
6. Update affected Key Contracts and the decision log in the implementation commit. Remove obsolete clipping
   behavior and invalidate stale parser caches if needed.

## Regression evidence

At the baseline, the account observations are:

| Case / resource | Evidence | Eligible NOT_FOUND | Future FOUND | audit_at |
|---|---|---|---|---|
| case_135 / account_1417 | evidence_13 | 2026-08-12T09:00:00Z | 2026-08-14T09:00:00Z | 2026-08-12T09:00:00Z |
| case_383 / account_5043 | evidence_36 | 2026-04-09T12:00:00Z | 2026-04-11T12:00:00Z | 2026-04-09T12:00:00Z |

The prior audit filtered future observations in memory, rebuilt each account obligation and substituted it into
the saved obligation list: PRESENT became ABSENT and planner status became COMPLETE in both cases. That does not
replace re-running discovery/assessment under the corrected code. Reproduce the transition without using the saved
diagnostics as inference inputs. Use participant evidence and resolved identifiers only.

Add `code/tests/test_observation_cutoffs.py` (planned). Exercise both sides of the boundary, future-only ownership,
same-file conflicting states, snapshot omissions, and expiry/retention fields. Include an end-to-end or assessment
test with grounded account linkage so the temporal change is tested beyond the selector alone.
