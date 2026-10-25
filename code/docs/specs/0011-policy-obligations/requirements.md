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
  SECURITY_AUDIT_LOG retention → `retention_until ≥ audit_at`; LEGAL_HOLD_RECORD → hold active per register/hold
  fields at audit_at. TRUE ⇒ the rule's action. UNKNOWN (no field) ⇒ the rule's action + `CONDITION_DEFAULTED`.
  **FALSE ⇒ the rules define no action** ⇒ `POLICY_UNDEFINED` blocker, no step for that resource; code never infers an
  inverse action (e.g. DELETE for expired retention).
- BACKUP_ARCHIVE: `restore_allowed=false` / `deletion_block=true` is the resource **state** BLOCKED (satisfied), not the
  condition. Condition FALSE only with explicit evidence that blocking is impossible (none seen) ⇒ normally UNKNOWN.
  Phase 0 saw no FALSE values (all retention_until 2031–2034); FALSE handling is tested with custom cases (0014).
- Resources with no applicable rule (cache, email_delivery, object, marketing without evidence) are excluded and
  counted in a report.

## Out of scope

Anything owned by another spec in `code/docs/FEATURE_STATUS.md`. Hard rules in `CLAUDE.md` apply.
