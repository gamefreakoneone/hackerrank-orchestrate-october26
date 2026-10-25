# Spec 0007 — evidence-parsers: requirements

**Depends on:** 0003, 0006

## Goal

Parse every non-image evidence file once into Observations with an inverted index.

## Requirements / acceptance criteria

- Parsers for SQL (24), JSON (28), logs (26, ≥6 formats), txt (1), PDF (4) produce `Observation`s per
  TECHNICAL_DESIGN §3.2. Records: SQL row, JSON object carrying `resource_id`, log trace_id group (or single
  line), PDF document, txt table row.
- `system_id`, `category`, `physical_copy`, `coverage` derived per TECHNICAL_DESIGN §5 Q1/Q2.
- Index: `by_resource[resource_id] -> list[Observation]`, `by_identifier[value] -> list[Observation]`.
- Per-file cache keyed by (sha256(file bytes), PARSER_VERSION) under `code/.cache/evidence/` (gitignored).
- Coverage report: every file yields ≥1 observation or is listed as empty with a reason.

## Out of scope

Anything owned by another spec in `code/docs/FEATURE_STATUS.md`. Hard rules in `CLAUDE.md` apply.
