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
  canonical order; COMPLETE has only VERIFICATION steps each with non-empty evidence_id; INCOMPLETE has ≥1
  FINDING, findings cite non-empty evidence_id, remediation and verification evidence_id == ""; every cited id
  exists in the manifest with captured_at ≤ that case's audit_at; no duplicate (operation, system_id, resource_id).
- `main.py` exits non-zero on validation errors.

## Out of scope

Anything owned by another spec in `code/docs/FEATURE_STATUS.md`. Hard rules in `CLAUDE.md` apply.
