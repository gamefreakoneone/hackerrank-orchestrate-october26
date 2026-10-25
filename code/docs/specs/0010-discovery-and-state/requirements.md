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
  4. account resolution at the **subject (user_id) level** (repeated requests of one subject, e.g. case_33 and
     case_52, share the account link; each request still applies its own cutoff):
     a. timestamped identity/reference links ≤ audit_at: pre-deletion snapshot rows, `customer_reference` /
        `subject_reference`, tombstone `subject_reference` (confirms the subject, no account id),
        LINK_RESOURCE_IDENTITY, readback trace groups. Unique ⇒ resolved (`via=ref_link`); several ⇒ rank by (b).
     b. otherwise rank workflow candidates — `DELETE_RECORD → account_service` with
        `requested_at ≤ event_time ≤ min(audit_at, reported_at + 15 min)` not linked to another user by any
        record ≤ audit_at — by `|event_time − reported_at|`, then resource_id. **Default: take the top candidate,
        flag `ACCOUNT_LINK_DEFAULT`** in diagnostics (measured: best of 5 rules tried, 8/20 on ambiguous samples).
     c. no candidate ⇒ flag `UNRESOLVED_ACCOUNT` (completion blocker, spec 0012).
     There is **no** one-to-one constraint across requests.
  5. anonymized/deleted analytics in the same workflow burst as the resolved account (fallback, flagged).
- State: for each resource, latest eligible observation by (captured_at, observed_at); any physical copy PRESENT ⇒
  PRESENT; `coverage=full_table` snapshot without the resource ⇒ ABSENT; activity results never set state, they
  only add candidates.
- Flows: ACTIVE if latest observation `enabled=true`/heartbeat enabled; backups: RESTORABLE if `restore_allowed`
  true or `eligible=true and deletion_block=false`.
- Target on samples: resource recall ≥ 85% (text/CSV ceiling 103/111 before PNGs), precision ≥ 80% after policy
  filtering. Phase-0b exact, cutoff-safe baseline: 77/111 found, 3 extra candidates.

## Out of scope

Anything owned by another spec in `code/docs/FEATURE_STATUS.md`. Hard rules in `CLAUDE.md` apply.
