# Spec 0009 — vision-extraction: requirements

**Depends on:** 0007, 0008

## Goal

Turn the 11 PNG screenshots into Observations.

## Requirements / acceptance criteria

- One Gemini call per PNG (cached) returning `list[VisionRecord]` (TECHNICAL_DESIGN §3.3b).
- Every resource_id must match RES_RE; every identifier must regex-validate and, for emails, appear in the
  identity universe (current or audit log) — otherwise dropped and counted.
- PNG observations enter the same index with `source_kind="png"`, category/system from the screen origin
  (`evidence_files.origin`) and `record_type`/status text.
- Report: per PNG, records extracted / dropped.

## Out of scope

Anything owned by another spec in `code/docs/FEATURE_STATUS.md`. Hard rules in `CLAUDE.md` apply.
