# Spec 0011 — policy-obligations: requirements

**Depends on:** 0010

## Goal

Turn discovered resources + rules into obligations with satisfied/unsatisfied state.

## Requirements / acceptance criteria

- Every discovered resource gets a data_category (record_type → container → event → Jev fallback via 0008,
  cached) and the rule's required end state (TECHNICAL_DESIGN §3.4).
- RETAIN categories (SECURITY_AUDIT_LOG, LEGAL_HOLD_RECORD) ⇒ required PRESENT; BACKUP_ARCHIVE ⇒ required BLOCKED;
  data flows ⇒ required DISABLED; ACCOUNT_TOMBSTONE ⇒ required REDACTED (user_id may remain; name, email, phone,
  email_hash must be null/absent).
- REDACTED satisfied iff no subject direct identifier remains in the latest observation; ANONYMIZED iff no subject
  identifier and no `customer_reference`/user_id link remains.
- Rule conditions are **tri-state** `TRUE / FALSE / UNKNOWN`, evaluated where a field exists:
  SECURITY_AUDIT_LOG retention → `retention_until ≥ audit_at` (TRUE ⇒ RETAIN/PRESENT; FALSE ⇒ treat as DELETE);
  LEGAL_HOLD_RECORD → hold active field/register entry at audit_at (FALSE ⇒ DELETE); BACKUP_ARCHIVE → restore can be
  blocked (FALSE ⇒ flag). No field ⇒ UNKNOWN ⇒ apply the default branch and flag `CONDITION_DEFAULTED` with the rule id.
  Phase 0 saw no FALSE values (all retention_until 2031–2034), so FALSE branches are tested with synthetic cases (0014).
- Resources with no applicable rule (cache, email_delivery, object, marketing without evidence) are excluded and
  counted in a report.

## Out of scope

Anything owned by another spec in `code/docs/FEATURE_STATUS.md`. Hard rules in `CLAUDE.md` apply.
