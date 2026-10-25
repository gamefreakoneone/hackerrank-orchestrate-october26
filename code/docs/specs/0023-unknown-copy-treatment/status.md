# Spec 0023 — Unknown copy treatment: status

**Status:** Completed
**Depends on:** 0022 — completed and pushed as `90f026cced401c885fb8519407cde4189bf381b8` on
`claude/specs-0017-0021-5s3kpe` (remote verified before this spec started).
**Working/push branch:** `claude/specs-0017-0021-5s3kpe`
**Implementation/publication:** committed as `spec 0023: preserve unknown treatment for every copy`; its pushed SHA
is recorded in the next spec's status / final report.

## What changed

- `obligations.py`: `current_state_by_physical_copy` builds DISABLED / BLOCKED states over the union of presence and
  treatment copies through `process_copy_state` (later absence ⇒ ABSENT; treatment fact ⇒ ACTIVE / required;
  present without treatment ⇒ UNKNOWN with rule `presence_without_treatment`). The treatment-only copy selection and
  the all-absent special case it needed are deleted. `current_state` lets a known violation win; otherwise any
  UNKNOWN copy makes the obligation UNKNOWN (unsatisfied, no proof, no finding).
- `pipeline.py`: `UNKNOWN_STATE` also fires when any copy state is UNKNOWN, so an aggregate ACTIVE cannot hide a
  second copy's uncertainty. Planner and validator unchanged: they already treat UNKNOWN as unsatisfied and emit no
  finding for it; output operations/fields are unchanged.
- 0018 preserved: an absent copy settles its flow; a retained archive absent everywhere stays ABSENT with
  `required_record_is_preserved=False` (REQUIRED_RECORD_MISSING). 0022 preserved: a post-cutoff treatment fact cannot
  resolve the unknown copy.

## Regression evidence

`code/tests/test_unknown_copy_treatment.py` (7 tests): review M1's counterexample for DATA_FLOW and BACKUP_ARCHIVE
through state → obligation → planner; later same-copy treatment resolves it (and a post-cutoff one does not); a
known ACTIVE primary with an unknown replica still yields finding + remediation + verification; an absent copy
settles a flow while a retained archive missing everywhere stays REQUIRED_RECORD_MISSING; copy-level uncertainty adds
`UNKNOWN_STATE` to a grounded sample assessment (case_05, which has no such flag on its own). All 7 failed on the
0022 baseline; all pass.

Dataset impact (offline, no cache, no PNG vision; participant evidence only):
`python code/main.py --cases all --offline --no-cache --out runs/corrective/0023_full_after.csv` vs the 0022 full
offline run: 0 changed rows; 203 DISABLED/BLOCKED obligations, 0 copy states UNKNOWN; validation 0 errors /
113 warnings. The live configuration (PNG vision records) is not measured.

## Scorer snapshot

| When / split | Revision / configuration | Status accuracy | Account linkage | Step F1 | Sequence exact |
|---|---|---|---|---|---|
| Before / dev | `90f026c`, `run_eval.py --split all -- --offline --no-cache` | 0.750 (15/20) | 0.350 (7/20) | 0.899 | 0.250 (5/20) |
| After / dev | this change, same configuration | 0.750 (15/20) | 0.350 (7/20) | 0.899 | 0.250 (5/20) |

Sample outputs byte-identical before/after.

## Checks

- `python -m pytest code/tests/test_unknown_copy_treatment.py code/tests/test_required_record_preservation.py
  code/tests/test_replica_state.py code/tests/test_obligations.py code/tests/test_validate.py
  code/tests/test_pipeline_e2e.py -q`: 61 passed.
- `python -m pytest code/tests -q` (RUN_LIVE unset): 178 passed, 2 skipped.
- `git diff --check`: clean. Saved release artifacts untouched.
