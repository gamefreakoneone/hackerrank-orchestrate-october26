# Spec 0020 — Reproducible evaluation reports: status

**Status:** Completed
**Implementation commit / publication:** code-freeze checkpoint `0d7c07d` (pushed; the revision recorded in the
bundle), then the `spec 0020: make evaluation reports reproducible and accurate` commit on
`claude/specs-0017-0021-5s3kpe`; its SHA and verified remote ref are in `FEATURE_STATUS.md` and the log.

## What changed

- `evaluation/capture_inputs.py` (new): at a committed revision (refuses uncommitted changes under `code/`) runs the
  five sample configurations, the custom cases, the discovery report and the test suites, copies their outputs into a
  bundle and writes `evaluation_inputs.json` (relative paths, SHA-256, revision, provider-key names present, LLM cache
  size, per-run model-call counts, test commands with exit codes). `SAMPLE_CONFIGURATIONS` is the single declaration
  of each configuration's flags.
- `evaluation/make_reports.py` (rewritten, model-free): loads the final manifest and the evaluation inputs
  (`--evaluation-inputs`, else the manifest's `evaluation_inputs` field), verifies paths, hashes, the 32-case coverage
  of predictions and diagnostics, declared configurations and the selected output checksum, and exits 1 with an
  actionable message otherwise. Revisions must match unless `--allow-revision-mismatch`, which labels the report
  "NOT a unified release". `--report-output-directory` stages reports without touching the selected ones.
  All narrative numbers are computed from per-case scores (status misses and their cause, grounded vs exact plans,
  evidence-id mismatches, discovery target verdict, custom pass count, test results). The hardcoded "every grounded
  sample has an exact plan" sentence, the unverified ablation explanation, the pytest subprocess and the `runs/`
  reads are gone; oracle-assisted state checks are labelled as such; costs are "estimated and unverified".
- `evaluation/run_custom.py` also writes structured `runs/custom/results.json`.
- README and `SUBMISSION_CHECKLIST.md`: validator command passes the producing run's diagnostics; capture and offline
  rebuild commands documented; `state_report.py` labelled oracle-assisted.

## Evidence

```text
python -m pytest code/tests/test_report_reproducibility.py code/tests/test_score.py code/tests/test_validate.py -q
25 passed
python -m pytest code/tests -q
144 passed, 2 skipped          (0019: 133; +11 reproducibility tests)
git diff --check               (clean)
```

`test_report_reproducibility.py` runs the real CLI in a fresh process on a fictional bundle, with provider
credentials removed and an unusable proxy: it rebuilds both reports, loads no provider/SDK module and creates no
`runs/`; missing predictions/diagnostics/custom results, an altered hash, wrong case coverage, a wrong declared
configuration, a revision mismatch and an altered selected output each exit 1 with an explicit message and render
nothing; an acknowledged mismatch is labelled; staging leaves a selected report untouched; "2 of the 4 samples with a
grounded account link have an exactly matching plan" is derived from the fixture.

Real rebuild (`code/evaluation/corrective_run/`, captured at `0d7c07d`, `evaluation_inputs.json` sha256 `09e82ebb…`):

```text
python code/evaluation/make_reports.py --evaluation-inputs code/evaluation/corrective_run/evaluation_inputs.json --report-output-directory code/evaluation/corrective_run/staged_reports
make_reports: evaluation inputs revision 0d7c07dd… != final run revision 375604e2…; pass --allow-revision-mismatch … (exit 1)
python code/evaluation/make_reports.py
make_reports: the final manifest names no evaluation_inputs; pass --evaluation-inputs PATH (exit 1)
… --allow-revision-mismatch → staged_reports/evaluation_report.md, usage_report.md ("NOT a unified release")
```

The selected `code/evaluation/evaluation_report.md` / `usage_report.md` and `final_run/` are unchanged (historical,
`375604e`); 0021 rebuilds them from a same-revision bundle. Validator on the selected output: with
`--diagnostics code/evaluation/final_run/diagnostics.jsonl` 0 errors / 104 warnings; without it 104 errors.

Bundle contents (all cached responses; default/ablation runs 49 cached calls each, deterministic 0 calls): custom
9/9 requests pass; tests `144 passed, 2 skipped`, metamorphic `4 passed`; discovery 77/111 (target unmet).

## Scorer snapshot

| When / split | Code revision / configuration | Status accuracy | Account linkage / coverage | Step F1 | Sequence exact |
|---|---|---|---|---|---|
| Before / dev | `52a1854` (0019), cached responses | 0.750 (15/20) | 7/20 correct, 13 ungrounded | 0.900 | 0.250 (5/20) |
| Before / all samples | `52a1854` (0019), cached responses | 0.719 (23/32) | 12/32 correct, 20 ungrounded | 0.896 | 0.281 (9/32) |
| After / dev | `0d7c07d`, cached responses | 0.750 (15/20) | 7/20 correct, 13 ungrounded | 0.900 | 0.250 (5/20) |
| After / all samples | `0d7c07d`, cached responses | 0.719 (23/32) | 12/32 correct, 20 ungrounded | 0.896 | 0.281 (9/32) |

Ablations (all samples, `0d7c07d`): deterministic 21/32, F1 0.855, exact 7/32; no-history 22/32, F1 0.886, exact 8/32;
trust-claims 23/32, F1 0.896, exact 9/32; ranked accounts 23/32, F1 0.891, exact 12/32 (8 right / 12 wrong guesses).
These are corrective-pass sample measurements, not the run that produced the selected root output.

## Rebuild and publication evidence

- Price sources were not verified (third-party trackers); the usage report says so. Ledger calls/tokens unchanged.
- Unavailable measurements are rendered "not measured" (full-dataset ablations; discovery/tests when absent).
- Implementation complete; the 0010 discovery target remains an unmet acceptance criterion (reported in the report).
