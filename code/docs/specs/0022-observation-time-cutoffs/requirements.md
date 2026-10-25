# Spec 0022 — Observation-time cutoffs: requirements

**Status:** Not started. **Depends on:** 0021 (historical implementation milestone).
Read `../../CORRECTIVE_HANDOFF_0022_0025.md` and finding B1 in
`../../reviews/0002-corrective-pass-review.md`.

## Confirmed defect

At `88a357e`, eligibility checks only file capture time and `observation_time()` clamps later observation
timestamps back to capture time. In case_135/account_1417 and case_383/account_5043, a FOUND record dated two days
after audit_at overrides an at-cutoff NOT_FOUND. These IDs are investigation/regression examples, never runtime keys.

## Acceptance criteria

- A state assertion must be available by audit_at and describe an observation/event at or before audit_at.
  Preserve the original timestamp; never turn a future observation into an at-cutoff fact by clipping it.
- Enforce this before identifier/reference discovery, ownership/account linking, category/policy selection,
  per-copy state, snapshot coverage and citation selection. Filtering only the final selected proof is insufficient.
- Distinguish observation/event time, file availability, snapshot time and business metadata. A future
  retention_until/expiry date is not a future observation and must not discard valid evidence.
- A record's created_at/updated_at does not automatically establish when its current state was observed.
  Use supported source semantics; make inconsistent or unknown timing explicit rather than inventing a time.
- A future row in a mixed-time trace/bundle must not contribute identifiers or coverage subjects to an earlier
  decision. Filtering rows must not manufacture an absence proof from an incomplete snapshot.
- Preserve valid same-copy supersession, named replica isolation, subject-scoped coverage, preservation rules,
  historical identifiers, the seven Step fields and canonical ordering.
- Reproduce the two saved-output defects and add small fictional counterexamples for future-only identity links,
  mixed-time records and valid future business dates. Assert code-derived outcomes, not hidden labels.
- Record comparable before/after sample dev metrics and a bounded affected-case check. Do not claim full-run
  status changes from a component-only substitution; retain explicit unknowns where proof is insufficient.

## Boundaries

Use the existing observation/coverage contracts and consumers. Update the parser cache version if cached facts
change. No new provider, fuzzy matching, case-specific rule, generator edit or broad timestamp framework.
The saved release remains historical until separately authorized regeneration and validation.
