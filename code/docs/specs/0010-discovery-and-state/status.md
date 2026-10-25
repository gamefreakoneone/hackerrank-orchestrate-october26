# Spec 0010 — discovery-and-state: status

**Status:** Completed (2026-10-25, overnight run) — the resource-recall **target is not met** (77/111 = 69% vs ≥ 85%);
the gap is bound by the grounding contract (details below), not by missing implementation.

## Evidence

```text
$ python -m pytest code/tests/test_discovery.py code/tests/test_timeline.py -q
11 passed
$ python code/tools/discovery_report.py --split dev
resource recall 49/71, extra 1; linkage grounded:correct 7, ungrounded 13 → accuracy 7/20, precision 7/7
$ python code/tools/discovery_report.py --split all
resource recall 77/111, extra 3; linkage grounded:correct 11, multi_grounded:correct 1, ungrounded 20
→ accuracy 12/32, precision 12/12; provenance of hits: identifier 75, reference 1, identifier+reference 1
$ python code/tools/state_report.py      # gold resources given; compares reconstructed state + proof
state_ok 104/111, state_unknown 7 (the 7 unreachable audit records), proof matches gold citation 75/75
$ python code/evaluation/run_eval.py --split dev       # pipeline is still the stub until spec 0012
status 0/20, F1 0.000 (unchanged)
All 518 requests: account link grounded 167, multi-grounded 0, ungrounded 351; provenance of the current account:
identifier 166, identifier+link_activity 1; 0 grounded accounts excluded as another user's.
```

## Linkage (separate from status accuracy)

| | before (Phase-0c baseline) | after (this spec) |
|---|---|---|
| unique grounded | 11 | 11 (all correct) |
| multi-grounded | 1 (case_17) | 1 (case_17: current account_4092, historical account_6523) |
| ungrounded | 20 | 20 |
| linkage precision | 12/12 | 12/12 |
| linkage accuracy / coverage | 12/32 | 12/32 |

**Grounded linkage did not rise above 12/32.** Every one of the 20 ungrounded sample cases was inspected: the gold
account appears in eligible evidence only as identifier-free rows (`profile: null`, status 404 in evidence_92) or not
at all, and its only connection to the request is a `DELETE_RECORD` claim in the workflow window, whose details carry
no subject identifier ("Deletion worker submitted primary profile account_X…"). The rows that would ground case_09,
case_26 and case_27 (evidence_06, evidence_02) are captured after audit_at. The PNG rows (spec 0009) add none. The
brief's new sources were all implemented: readback trace groups (complete `lookup_key` + resource id), service-export
`profile_lookups` with a populated profile, history `record_lookup`/handover rows (`subject_reference` = email +
account id), LINK_RESOURCE_IDENTITY, and `source_resource_id` edges. None reaches these 20 accounts, so they stay
`ACCOUNT_UNGROUNDED` with ranked candidates in diagnostics only (top-ranked would be right 8/20, unchanged).

Recall gap (34 misses): 20 ungrounded accounts, 7 anonymized analytics records (only identifier-free rows plus
ANONYMIZE_RECORD claims — same situation), 7 audit records with no eligible evidence at all. 77/111 is therefore the
reach under the grounding contract on these samples; the ≥ 85% target (set before the 0c grounding decision) is
not attainable without ungrounded links, which the contract forbids.

## Scorer snapshot (dev)

| | Status acc | Account linkage | Step F1 | Seq exact |
|---|---|---|---|---|
| before (0009) | 0.000 | not measured | 0.000 | 0.000 |
| after | 0.000 | 7/20 (discovery report; pipeline not wired until 0012) | 0.000 | 0.000 |

## Notes

- `discovery.py`: exact identifier links (names excluded: a name never links), LINK_RESOURCE_IDENTITY naming a subject
  email/user id, `source_resource_id` reference edges in both directions from grounded resources, RESTORE_BACKUP
  "repopulated downstream resource" as an ungrounded candidate (`restore_claim`), ≤ 3 expansion rounds.
- `account_link.py`: grounded account_service resources, minus any named by another known user's identifiers; current =
  most recent link time, older ones historical; ungrounded ⇒ workflow candidates ranked by |t − reported_at| within
  `[requested_at, min(audit_at, reported_at + 15 min)]`, excluding accounts named for another user (diagnostics only).
- `timeline.py`: latest establishing file observation per dimension (presence, enabled, restorable; within one capture
  any copy present/active wins); observed absence (404 / rows=0 / NOT_FOUND / hits 0) is cited as observed; absence by
  omission per TECHNICAL_DESIGN §5 Q2 **plus** [overnight] rule: when the resource was last seen in a replica snapshot
  copy, only a snapshot of that same copy can show it gone (case_05 replica drift; a later primary-only inventory no
  longer overrides it); state-check activity only when no file establishes the dimension; `_completed` read events count
  as presence. Trace merging now ignores infrastructure lines (`cache_lookup` result=miss had been read as absence).
- `tools/state_report.py` and `tools/discovery_report.py` read gold for evaluation only.
