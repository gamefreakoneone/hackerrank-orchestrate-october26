# Spec 0017 — Replica state and proof: design

## Existing failure and owned changes

`ghostaudit/timeline.py:_latest` selects one latest file globally; `state_at` bypasses replica coverage once
that selection says absent. `ghostaudit/obligations.py:current_state` examines only its selected observation.
Replace that behavior in these functions and their direct consumers, not with a parallel decision engine.

1. Inventory actual copy/scope metadata in SQL tables and structured/log observations. Normalize only supported
   aliases. Do not assume a bare `service_read` or `export` observation covers an identified replica.
2. Group eligible observations by established copy scope. Preserve unscoped observations separately when they
   cannot safely replace scoped evidence. Name collections for their contents, e.g.
   `latest_observation_by_physical_copy` and `uncleared_physical_copies`.
3. Within a copy, select the latest state observation using the time semantics of its source: snapshot time
   for a snapshot, event/read time for a read, and manifest capture time as the availability gate. A row's
   `updated_at` alone is not necessarily when its existence was observed. Record the source/time rule used.
4. Apply absence-by-omission only to the scope covered by an eligible, non-superseded snapshot. Keep the
   no-surviving-candidate behavior UNKNOWN. Explicit readback evidence can also clear its established scope.
5. Return enough per-copy facts in `ResourceState` for `current_state` to evaluate presence, PII exposure,
   enabled state and restoration state across the relevant copies. Use a small mapping/dataclass only as
   needed by those consumers. Keep aggregate compatibility fields only if an existing caller needs them.
6. Choose the finding proof from the actual violating copy. Completion requires the relevant scopes to be
   established compliant, not merely a convenient latest citation. Preserve contributing proof IDs and
   scope decisions in diagnostics; do not claim one file proves an unobserved copy's state.

If evidence cannot identify the necessary scope, keep the uncertainty explicit. Do not guess a copy identity
from a resource number, case family, workflow timing or sample answer.

## Regression cases

Add `code/tests/test_replica_state.py` (planned) with small fictional fixtures:
- replica present, later primary-only 404;
- replica exposes PII, later primary clean;
- both copies subsequently established absent or appropriately treated;
- later same-copy state supersedes earlier state within one capture;
- an unrelated copy and a post-cutoff observation cannot clear the target;
- a format-only label cannot be mistaken for all-replica coverage;
- emitted proof identifies the violating copy, not the newer clean source.

Exercise both state reconstruction and obligation/planner output. Update Key Contracts and the decision log
in this implementation commit; remove the superseded global-selection path once all callers use the fix.
