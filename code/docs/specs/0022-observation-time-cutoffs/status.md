# Spec 0022 — Observation-time cutoffs: status

**Status:** Completed
**Working/push branch:** `claude/specs-0017-0021-5s3kpe`
**Audited baseline:** `88a357ea152601aeca3ce5cc98e0fd764597b1c6`; implementation started from `afb5017`.
**Implementation/publication:** committed as `spec 0022: enforce observation-time cutoffs`; the pushed SHA is
recorded in the next spec's status / final report (no self-SHA in this commit).

## What changed

- `evidence/index.py`: `state_observed_at(item)` = record/snapshot time, else capture time (never clipped);
  `eligible(item, audit_at)` requires `max(captured_at, state_observed_at) <= audit_at`. Every influence path already
  used `eligible` (discovery identifier and reference links, `account_link.other_owners`, `resource_category`, the
  policy condition observations in `pipeline`, per-copy state, omission coverage and therefore citations), so one rule
  covers them all; no second temporal engine.
- `timeline.py`: deleted `observation_time` / `coverage_time` and their `min(..., captured_at)` backdating; ordering
  uses `state_observed_at`.
- `evidence/json_.py`: a bundle record dated after its snapshot names no covered subject; it stays in
  `resource_ids`, so filtering never manufactures an omission/absence proof.
- Parser cache version `0017.2` → `0022.1`.
- Inventory: SQL observations use the snapshot header; JSON uses record `observed_at`/`recorded_at`, else the
  snapshot/context time, else capture time; logs use the last line of the trace group (a group whose last line is
  after audit_at contributes nothing, including identifiers); txt rows use their observed_at; PDFs/PNGs have no
  record time and fall back to capture time (the document/screen establishes state when captured). Business dates
  (`retention_until`, `retained_until`) remain fields read by the policy condition. `created_at`/`updated_at` are
  not used as observation time. Identity uses `updated_at`/`event_time <= audit_at` (unchanged). The PNG
  `email_universe` only filters OCR identifiers for validity; links still require the cutoff-filtered subject
  identifiers, so a post-cutoff email cannot create a pre-cutoff link.
- A dataset-wide scan found exactly two parsed records dated after their file's capture (evidence_13/account_1417,
  evidence_36/account_5043), no log line after its file's capture and no snapshot dated after its file.

## Regression evidence

`code/tests/test_observation_cutoffs.py` (8 tests): the two participant regressions through `assess` + `plan`, and
fictional cases for same-file conflicting states on both sides of the boundary, a future-only identity link, a
mixed-time trace group, a bundle record dated after its snapshot, a future snapshot, and a future retention date.
On the baseline 7/8 failed (the retention-date guard passes before and after, as intended); all 8 pass after.

Bounded affected-case check (offline, no cache, no vision), `python <scratch>/affected_0022.py` running
`assess` + `plan` on the full dataset:

```text
before: case_135 INCOMPLETE ['CONDITION_DEFAULTED'] [('account_1417', 'PRESENT', 'ABSENT', 'evidence_13')] 4 steps
before: case_383 INCOMPLETE ['CONDITION_DEFAULTED'] [('account_5043', 'PRESENT', 'ABSENT', 'evidence_36')] 4 steps
after:  case_135 COMPLETE ['CONDITION_DEFAULTED'] [('account_1417', 'ABSENT', 'ABSENT', 'evidence_13')] 2 steps
after:  case_383 COMPLETE ['CONDITION_DEFAULTED'] [('account_5043', 'ABSENT', 'ABSENT', 'evidence_36')] 2 steps
```

Full offline/no-cache run (`python code/main.py --cases all --offline --no-cache --out runs/corrective/0022_full_*.csv`,
before = stashed baseline code, after = this change): 518 rows each, validation 0 errors / 113 warnings both, exactly
two rows differ — case_135 and case_383, INCOMPLETE → COMPLETE. This is an offline configuration (no PNG vision, no
LLM cache), not the live release configuration; the saved root `output.csv` was not touched.

## Scorer snapshot

| When / split | Revision / configuration | Status accuracy | Account linkage | Step F1 | Sequence exact |
|---|---|---|---|---|---|
| Before / dev | `afb5017`, `run_eval.py --split all -- --offline --no-cache` | 0.750 (15/20) | 0.350 (7/20) | 0.899 | 0.250 (5/20) |
| After / dev | this change, same configuration | 0.750 (15/20) | 0.350 (7/20) | 0.899 | 0.250 (5/20) |

The 32-sample outputs are byte-identical before/after (no sample case has a record dated after its file's capture).
All-sample offline: 21/32, F1 0.855, exact 7/32 both. The preserved live sample bundle (23/32, F1 0.895775, exact
9/32) is a different configuration and is not comparable.

## Checks

- `python -m pytest code/tests/test_observation_cutoffs.py code/tests/test_timeline.py code/tests/test_replica_state.py
  code/tests/test_discovery.py code/tests/test_identity.py code/tests/test_pipeline_e2e.py -q`: 44 passed.
- `python -m pytest code/tests -q` (RUN_LIVE unset): 171 passed, 2 skipped.
- `git diff --check`: clean.
- Output/diagnostics/report changes: none to the saved release (`output.csv`, `final_run/`, `corrective_run/`).
