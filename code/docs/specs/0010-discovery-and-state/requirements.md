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
     a. **grounded** links ≤ audit_at: a subject identifier and the account id in one record — pre-deletion
        snapshot rows, `customer_reference` / `subject_reference`, LINK_RESOURCE_IDENTITY, readback trace groups
        (tombstone `subject_reference` confirms the subject but names no account). Unique ⇒ `via=grounded`.
        Several ⇒ `ACCOUNT_MULTI_GROUNDED`: the account with the most recent grounded link (latest eligible
        captured_at of a linking record) is the **current** account; every older grounded account stays as a
        **historical** account obligation (it may still retain data) unless evidence excludes it (linked to another
        user, or shown to be the same record). Never dropped silently. case_17: current account_4092 (09-15 link),
        historical account_6523 (03-10 link; one extra step vs gold, accepted).
     b. no grounded link ⇒ flag `ACCOUNT_UNGROUNDED` (completion blocker, spec 0012). Workflow candidates —
        `DELETE_RECORD → account_service` with `requested_at ≤ event_time ≤ min(audit_at, reported_at + 15 min)`
        not linked to another user ≤ audit_at — are **ranked** by `|event_time − reported_at|` and written to
        diagnostics only; a ranked candidate never grounds the account (best rule is wrong on 12/20 ambiguous samples).
     There is **no** one-to-one constraint across requests. Main goal of this spec: raise grounded linkage above
     12/32 with new grounded sources (PNG rows from 0009, more reference fields), measured as linkage accuracy.
  5. anonymized/deleted analytics: grounded links only (same rule as accounts); burst co-membership with the
     account is a ranked hint in diagnostics, not a link.
- State: for each resource, latest eligible observation by (captured_at, observed_at); any physical copy PRESENT ⇒
  PRESENT; absence by omission per the `SnapshotCoverage` rule (TECHNICAL_DESIGN §5 Q2). Activity: **operational
  claims** (DELETE/REDACT/ANONYMIZE/BLOCK_RESTORE/DISABLE_DATA_FLOW/RETAIN/SYNC/INDEX/UPDATE/CREATE_EXPORT/SEND_EMAIL/
  REFRESH_CACHE/CLASSIFY_REQUEST/RESTORE_BACKUP) never set state — they add candidates and risks only;
  **state-check events** (CHECK_DATA_FLOW, CHECK_RESTORE_ACCESS) are parsed into observations with
  `source_kind="activity"` and used only when no file establishes the state.
- Flows: ACTIVE if latest observation `enabled=true`/heartbeat enabled; backups: RESTORABLE if `restore_allowed`
  true or `eligible=true and deletion_block=false`.
- Target on samples: resource recall ≥ 85% (text/CSV ceiling 103/111 before PNGs), precision ≥ 80% after policy
  filtering. Phase-0b exact, cutoff-safe baseline: 77/111 found, 3 extra candidates.

## Out of scope

Anything owned by another spec in `code/docs/FEATURE_STATUS.md`. Hard rules in `CLAUDE.md` apply.
