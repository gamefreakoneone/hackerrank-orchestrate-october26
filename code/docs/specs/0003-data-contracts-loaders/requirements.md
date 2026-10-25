# Spec 0003 — data-contracts-loaders: requirements

**Depends on:** 0001

## Goal

Typed, timezone-aware loaders for every CSV and the Key Contract models.

## Requirements / acceptance criteria

- Pydantic v2 models: `Request`, `Identity`, `AuditEvent`, `Activity`, `Rule`, `EvidenceFile`, `Step`,
  `Observation`, `Obligation` exactly as TECHNICAL_DESIGN §3.
- All datetimes are aware UTC. `case_id` numeric key helper.
- `load_dataset(root) -> Dataset` returns all tables; `sample=True` swaps in `sample_deletion_requests.csv`.
- Loaders never open `sample_output.csv`.

## Out of scope

Anything owned by another spec in `code/docs/FEATURE_STATUS.md`. Hard rules in `CLAUDE.md` apply.
