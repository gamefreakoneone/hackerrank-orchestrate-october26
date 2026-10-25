# Spec 0004 — serializer-validator: requirements

**Depends on:** 0003

## Goal

Deterministic output writer and a hard validator for every output rule.

## Requirements / acceptance criteria

- `serialize.write_output(rows, path)`: header `case_id,deletion_status,steps_json`, rows sorted by `case_key`,
  steps canonical-sorted and renumbered 1..n, compact sorted-key JSON.
- `validate.validate_output(path, requests) -> list[str]` (empty = valid) checking: exact header; one row per
  request case_id, no extras; numeric sort; status enum; NOT_APPLICABLE ⇔ `[]`; JSON array of objects with
  exactly the 7 keys; step_no consecutive from 1; phase/operation/state consistent (OP_PHASE/OP_STATE);
  canonical order; COMPLETE has only VERIFICATION steps each with non-empty evidence_id; findings cite a
  non-empty evidence_id; remediation and INCOMPLETE verification evidence_id == ""; every cited id is a manifest
  `file_id` with captured_at ≤ audit_at, or (fallback) an `activity_id` / `audit_id` with event_time ≤ audit_at;
  no duplicate (operation, system_id, resource_id).
- INCOMPLETE with zero FINDING steps (or `[]`) is a **warning**, not an error, only when the case diagnostics carry a
  completion-blocker flag (TECHNICAL_DESIGN §3.5); otherwise it is an error.
- Validator also reports the count of activity/audit citations (expected to be rare; files are preferred).
- `main.py` exits non-zero on validation errors.

## Out of scope

Anything owned by another spec in `code/docs/FEATURE_STATUS.md`. Hard rules in `CLAUDE.md` apply.
