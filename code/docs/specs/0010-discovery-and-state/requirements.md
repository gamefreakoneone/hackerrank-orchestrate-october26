# Spec 0010 — discovery-and-state: requirements

**Depends on:** 0006, 0007 (0009 optional)

## Goal

Find every resource relevant to the subject and its state at audit_at.

## Requirements / acceptance criteria

- Discovery (only eligible evidence/activity, captured_at/event_time ≤ audit_at):
  1. identifier-linked records (Subject.matches on any identifier field of the record/trace group);
  2. LINK_RESOURCE_IDENTITY activity naming a subject identifier;
  3. one-hop expansion via reference fields (`source_resource_id`, `customer_reference == user_id`,
     `subject_reference`, `RESTORE_BACKUP` "repopulated downstream resource X");
  4. account resolution: exactly one account_service resource per deletion case — identifier-linked if possible,
     otherwise global assignment (below);
  5. anonymized/deleted analytics in the same workflow burst as the resolved account (fallback).
- Global assignment: candidates = `DELETE_RECORD → account_service` in `[requested_at, reported_at+15m]`; remove
  accounts owned (identifiers) by another user or targeted by CLASSIFY_REQUEST; solve one-to-one across all
  requests (min total |event_time − reported_at|, tie → lower case number); unresolved ⇒ no account step.
- State: for each resource, latest eligible observation by (captured_at, observed_at); any physical copy PRESENT ⇒
  PRESENT; `coverage=full_table` snapshot without the resource ⇒ ABSENT; activity results never set state, they
  only add candidates.
- Flows: ACTIVE if latest observation `enabled=true`/heartbeat enabled; backups: RESTORABLE if `restore_allowed`
  true or `eligible=true and deletion_block=false`.
- Target on samples: resource recall ≥ 85% (ceiling 103/111), precision ≥ 80% after policy filtering.

## Out of scope

Anything owned by another spec in `code/docs/FEATURE_STATUS.md`. Hard rules in `CLAUDE.md` apply.
