# Spec 0017 — Replica state and proof: status

**Status:** Completed
**Implementation commit / publication:** the `spec 0017: correct replica state and proof aggregation` commit on
`claude/specs-0017-0021-5s3kpe` (cloud session's designated push branch, started from `origin/claude/eager-cray-7fhtkf`
@ `bf79d4a`). The SHA and the verified remote ref are recorded in `FEATURE_STATUS.md`/`MORNING_REPORT.md` and the log.

## What changed

- `timeline.py`: the global `_latest` selector and the `required_copy` special case are deleted. State is now
  reconstructed per storage copy (`latest_fact_by_physical_copy`, `presence_by_physical_copy`) and returned as
  `ResourceState.{presence,enabled,restorable}_by_physical_copy`.
  - Copy identity comes only from SQL table names (`primary`, `failover_replica`, `read_replica`, `reporting_replica`,
    `replica_eu_west`, `replica_ap_south`). Format labels (`export`, `bundle`, `service_read`, `screen`, `document`)
    read the logical service, i.e. its system of record (`primary`); they never clear a named replica.
  - Within a copy the latest observation wins by **observation time** (SQL snapshot header, read/log line time,
    record `observed_at`/`recorded_at`, bundle snapshot time), then file availability; manifest `captured_at` stays
    the cutoff gate. A row's `updated_at` is no longer used as its observation time (`sql.py`, parser `0017.2`).
  - A copy last seen present is cleared only by a later snapshot **of that copy** omitting the resource.
    The never-observed rule (§5 Q2 latest-with-replica, else latest, else UNKNOWN) is unchanged.
  - Records-assurance bundles are exported for a batch of subjects (every bundle lists ~10 `user_*` references;
    `evidence_51` omits `audit_record_1596` 23 s after a successful read of it). `SnapshotCoverage.covered_subjects`
    now carries those user_ids and a bundle omission counts only for them. SQL snapshots stay full-table coverage.
- `obligations.py`: each copy gets its own current state; any violating copy wins and is the cited proof, else the
  latest compliant copy is cited; no established copy ⇒ UNKNOWN. `Obligation.copy_states` (diagnostics only) keeps
  every contributing copy, its state, proof and rule. Output schema, ordering and the seven Step fields are unchanged.
- `pipeline.py`/`tools/state_report.py` pass the subject `user_id`; `state_report` now uses the engine's own per-copy
  evaluation instead of a parallel copy of it.

## Evidence

Counterexamples reproduced on the baseline (`runs/corrective/0017_tests_before_fix.txt`, code `bf79d4a` + new test):
`7 failed, 2 passed` — including the review's two false-COMPLETE cases (replica present + newer primary-only 404 →
ABSENT/satisfied; replica PII + newer clean primary → REDACTED/satisfied), same-capture supersession, unrelated /
post-cutoff copy, format-label coverage and newer packaging of an older read.

After the fix:

```text
python -m pytest code/tests/test_replica_state.py code/tests/test_timeline.py code/tests/test_obligations.py code/tests/test_pipeline_e2e.py -q
37 passed
python -m pytest code/tests -q
118 passed, 2 skipped        (baseline 108 passed, 2 skipped; +10 tests in test_replica_state.py)
git diff --check             (clean)
```

## Scorer snapshot

Both runs use the same inputs and providers: `before` ran live (cold cache: Jev intent 32, Gemini vision 11, Azure
adjudication 4, Jev category fallback 2 = 49 calls) at `bf79d4a`; `after` replayed exactly those cached responses
(49 cached rows, 0 new calls). The before run differs from the historical 0.898 step F1 only through fresh live
provider responses; it is the comparable baseline.

| When / split | Code revision / configuration | Status accuracy | Account linkage / coverage | Step F1 | Sequence exact |
|---|---|---|---|---|---|
| Before / dev | `bf79d4a`, live providers | 0.750 (15/20) | 7/20 correct, 13 ungrounded | 0.900 | 0.250 (5/20) |
| Before / all samples | `bf79d4a`, live providers | 0.719 (23/32) | 12/32 correct, 20 ungrounded | 0.896 | 0.281 (9/32) |
| After / dev | 0017 working tree, same cached responses | 0.750 (15/20) | 7/20 correct, 13 ungrounded | 0.900 | 0.250 (5/20) |
| After / all samples | 0017 working tree, same cached responses | 0.719 (23/32) | 12/32 correct, 20 ungrounded | 0.896 | 0.281 (9/32) |

The before and after sample outputs are byte-identical (`sha256 c930afc9…` for both CSVs).

Oracle-assisted component diagnostic (`code/tools/state_report.py`, gold resource IDs supplied): state 103/111
(baseline 104/111), proofs 75/75. The one change is `case_23 account_410` → UNKNOWN: it was never observed and the
only non-superseded omissions were bundles exported for other subjects (`evidence_07`, `evidence_51`), which do not
establish its absence. Gold verifies it with an empty evidence id in an INCOMPLETE case; the account is ungrounded in
the pipeline, so the output is unaffected.

Full-dataset state impact (offline, all 518 requests through `assess`/`plan` without the intent gate, cached PNG
facts, before vs after): 3 obligations change, all PRESENT → ABSENT; statuses 468 INCOMPLETE and 48 COMPLETE
unchanged, 2 INCOMPLETE → COMPLETE, **0 COMPLETE → INCOMPLETE** (no saved COMPLETE row depended on a primary read
hiding a replica).
- `case_86 account_8473`: `evidence_08` lookup FOUND 08-31, then NOT_FOUND 09-06 for the same resource (later
  same-copy observation supersedes; the baseline preferred "present" within one file).
- `case_390 account_7618`: `evidence_36` FOUND 04-03, NOT_FOUND 04-09 (same rule).
- `case_33 export_1260`: seen on screen `evidence_23` (06-18); the later inventory `evidence_81` (07-03,
  `snapshot_scope` includes export_service) omits it from the primary `customer_exports` table. The baseline kept it
  present only because its file pool preferred an older replica-covering file.

## Failures, decisions and publication

- Decision: format labels map to the system of record; only SQL table names identify replicas. Logs carry
  `region`/`instance`/`shard`, but those describe the serving application instance, not a storage copy, so they are
  not mapped to `replica_*` tables.
- Decision: bundle coverage is subject-scoped (evidence above); SQL snapshots remain full-table coverage as the
  sample citations require (`evidence_54` proves absence for subjects it does not reference).
- No sample answer, provider or model call was changed. No acceptance check failed.
