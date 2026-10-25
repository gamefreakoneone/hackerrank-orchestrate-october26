# Spec 0006 — identity-resolution: requirements

**Depends on:** 0003

## Goal

Resolve the subject and every identifier valid at or before audit_at.

## Requirements / acceptance criteria

- `resolve(request, dataset) -> Subject` with `user_id`, `emails`, `phones`, `names`, `email_hashes`
  (sha256 of every email, plus every hash in the audit log), `current` vs `historical` flags.
- Request email may be current or historical (100/517 historical-only); match exact string after strip, then
  lower-case as fallback.
- Only audit rows with `event_time ≤ audit_at` contribute; post-cutoff rows are **never read** (no reverting of later
  changes). Identifiers = current snapshot values + old/new values of pre-cutoff rows. If the snapshot's
  `updated_at > audit_at`, flag `IDENTITY_SNAPSHOT_AFTER_CUTOFF` (measured 0/550 requests; also 0/550 subjects have
  post-cutoff audit rows, so strict and "revert" give identical identifiers — `code/tools/p0_q6_identity_cutoff.py`).
- Unknown email ⇒ Subject with only the email and its hash (no crash).

## Out of scope

Anything owned by another spec in `code/docs/FEATURE_STATUS.md`. Hard rules in `CLAUDE.md` apply.
