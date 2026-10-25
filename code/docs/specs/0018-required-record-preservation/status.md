# Spec 0018 — Required record preservation: status

**Status:** Completed
**Implementation commit / publication:** the `spec 0018: enforce required record preservation` commit on
`claude/specs-0017-0021-5s3kpe`; the SHA and verified remote ref are recorded in `FEATURE_STATUS.md` and the log.

## What changed

- `policy.preservation_required(category, rule)`: REDACT, ANONYMIZE and RETAIN keep the record (AGENTS.md §6.4
  "keep the record ..."); DELETE does not; a data flow is a process, not retained business data.
- `obligations.py`: `SATISFYING` is replaced by `TREATMENT_SATISFIED_BY` (per-copy treatment: an absent copy
  exposes and copies nothing) plus a separate preservation predicate `record_is_preserved` (some copy present;
  a tombstone only while it keeps the subject's stable `user_id`). `satisfied` = treatment satisfied **and**, when
  preservation is required, `required_record_is_preserved is True`.
  - A kept record absent in every established copy reports `current="ABSENT"` with the absence proof (never
    relabelled REDACTED/BLOCKED); no presence fact ⇒ UNKNOWN (UNKNOWN_STATE), distinct from proven absence.
  - For a compliant kept record the cited proof is a present compliant copy, so a COMPLETE verification cites
    evidence of both preservation and treatment.
  - For DISABLED/BLOCKED, a later absence of the same copy now supersedes an older enabled/restorable fact (a removed
    flow cannot copy data; a removed archive is then a missing retained record).
- `Obligation.preservation_required` / `required_record_is_preserved` (diagnostics). New blocker
  `REQUIRED_RECORD_MISSING` (pipeline flags it when a kept record is not preserved). `BLOCKER_FLAGS` now lives once
  in `models.py`, used by planner and validator (their duplicate sets are deleted); the scorer reports the flag.
- `planner.py`: findings/remediation only for `treatment_violated` (something present that must not be). A missing
  kept record gets no invented finding, restore operation or evidence id; its future verification (required end
  state, `evidence_id=""`) stays in the INCOMPLETE plan.
- `tools/state_report.py` evaluates gold resources through `build_obligation` (MISSING verdict for unpreserved
  records) instead of reimplementing the predicates.

## Evidence

Baseline reproduction at the 0017 commit `4f2a05a` (`runs/corrective/0018_baseline_repro.txt`):

```text
tombstone_9101 required REDACTED current ABSENT satisfied True -> COMPLETE [('VERIFY_RECORD_REDACTED', 'evidence_952')]
backup_9102 required BLOCKED current BLOCKED satisfied True -> COMPLETE [('VERIFY_RESTORE_BLOCKED', 'evidence_951')]
```

The new test module cannot even import the preservation API on the baseline. After the fix:

```text
python -m pytest code/tests/test_required_record_preservation.py code/tests/test_policy.py code/tests/test_obligations.py code/tests/test_validate.py code/tests/test_pipeline_e2e.py -q
49 passed
python -m pytest code/tests -q
130 passed, 2 skipped      (0017: 118 passed; +11 preservation tests, +1 unknown-presence backup case)
git diff --check           (clean)
```

`test_required_record_preservation.py` covers: missing tombstone, retained backup and shared support conversation
(INCOMPLETE, REQUIRED_RECORD_MISSING, only the future verification step); unknown presence (UNKNOWN_STATE, not
missing); clean tombstone with stable reference passes, without it does not; exposed tombstone is a finding;
blocked vs restorable backup; REDACT record never planned as DELETE; absence still satisfies DELETE and a removed
data flow; the validator accepts the blocked plan only with the shared blocker flag.

## Scorer snapshot

Same cached provider responses for before and after (no new model calls).

| When / split | Code revision / configuration | Status accuracy | Account linkage / coverage | Step F1 | Sequence exact |
|---|---|---|---|---|---|
| Before / dev | `4f2a05a` (0017), cached responses | 0.750 (15/20) | 7/20 correct, 13 ungrounded | 0.900 | 0.250 (5/20) |
| Before / all samples | `4f2a05a` (0017), cached responses | 0.719 (23/32) | 12/32 correct, 20 ungrounded | 0.896 | 0.281 (9/32) |
| After / dev | 0018 working tree, cached responses | 0.750 (15/20) | 7/20 correct, 13 ungrounded | 0.900 | 0.250 (5/20) |
| After / all samples | 0018 working tree, cached responses | 0.719 (23/32) | 12/32 correct, 20 ungrounded | 0.896 | 0.281 (9/32) |

Sample outputs before/after are byte-identical; REQUIRED_RECORD_MISSING fires on 0 samples. Oracle-assisted state
diagnostic unchanged: 103/111 states, 75/75 proofs.

Full-dataset state impact (offline, all 518 requests through `assess`/`plan`, cached PNG facts, 0017 vs 0018):
0 obligation or status changes. One kept record is absent: `case_34 audit_record_3753` (RETAIN, ABSENT via
`evidence_05`), already unsatisfied; it now also carries the explicit REQUIRED_RECORD_MISSING blocker. This matches
the review: no saved row relied on absence satisfying a preserve-and-treat obligation.

## Failures, decisions and publication

- Decision: preservation is derived from the rule action, not per resource; the tombstone stable-reference check
  uses the subject's resolved `user_id` (AGENTS.md §6.5 "preserve the stable subject reference").
- Unsupported remediation gap (documented, not invented): the schema has no operation to restore a missing retained
  record, so such a case is INCOMPLETE with a blocker and only the future verification step.
- No sample answer, provider or model call changed. No acceptance check failed.
