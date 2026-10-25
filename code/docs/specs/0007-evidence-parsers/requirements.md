# Spec 0007 — evidence-parsers: requirements

**Depends on:** 0003, 0006

## Goal

Parse every non-image evidence file once into Observations with an inverted index.

## Requirements / acceptance criteria

- Parsers for SQL (24), JSON (28), logs (26, ≥6 formats), txt (1), PDF (4) produce `Observation`s per
  TECHNICAL_DESIGN §3.2. Records: SQL row, JSON object carrying `resource_id`, log trace_id group (or single
  line), PDF document, txt table row.
- `system_id`, `category`, `physical_copy` derived per TECHNICAL_DESIGN §5 Q1/Q2; `evidence_id` = file_id.
- Also parse state-check activity rows (CHECK_DATA_FLOW, CHECK_RESTORE_ACCESS) into `Observation`s with
  `source_kind="activity"`, `evidence_id` = activity_id, `captured_at` = event_time (contract §3.2).
- Separately from Observations, emit one `SnapshotCoverage` (TECHNICAL_DESIGN §3.3) per complete table/collection
  per file — **including empty ones** (e.g. `evidence_51` account `customer_profiles` collection with 0 records,
  `evidence_90` inventory with 0 profile rows) — with system_id, collection, physical_copy, scope, captured_at,
  row_count and the set of resource_ids present.
- Index: `by_resource[resource_id] -> list[Observation]`, `by_identifier[value] -> list[Observation]`,
  `coverage[system_id] -> list[SnapshotCoverage]` sorted by captured_at.
- Per-file cache keyed by (sha256(file bytes), PARSER_VERSION) under `code/.cache/evidence/` (gitignored).
- Coverage report: every file yields ≥1 observation or is listed as empty with a reason.

## Out of scope

Anything owned by another spec in `code/docs/FEATURE_STATUS.md`. Hard rules in `CLAUDE.md` apply.
