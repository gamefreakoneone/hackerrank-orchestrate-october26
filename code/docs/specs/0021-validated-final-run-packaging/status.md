# Spec 0021 — Validated final run and packaging: status

**Status:** Completed
**Producing code-freeze commit:** `b90914b` (pushed before the run; the evaluation bundle was pushed as `67bb114`,
artifacts only)
**Completion commit / publication:** the `spec 0021: validate final run and submission bundle` commit on
`claude/specs-0017-0021-5s3kpe`; SHA and verified remote ref in the log and the final report.

## What changed

- `main.py`: candidate first. Predictions and diagnostics go to run-owned `.<name>.<run_id>.staged` files, are
  validated, and only then replace `--out` and its diagnostics; a failed validation exits 1, leaves the previous files
  and keeps the rejected candidate; a failed generation writes nothing. `--run-manifest-output` names the manifest,
  which records the revision, `uncommitted_producing_code`, SHA-256 of output/diagnostics/usage ledger, validation
  counts and `published`. A `--case` subset cannot target the selected `output.csv`.
- `ghostaudit/provenance.py` (new, model-free): revision, uncommitted producing code (`PRODUCING_CODE_PATHSPECS`),
  hashing — shared by `main.py`, `capture_inputs.py`, `make_reports.py`, `finalize_run.py`.
- `tools/finalize_run.py` (new, thin): refuses subset, ablation/offline, uncommitted-code, unpublished, altered or
  invalid candidates and evaluation inputs from another revision; renders both reports, stages all files, replaces
  `final_run/`, the reports and `output.csv` (last) by renames, re-checks hashes and a re-render; an interruption
  reports the run id and the previous bundle's location (not claimed atomic).
- `.gitattributes`: `output.csv`, `code/evaluation/final_run/**`, `code/evaluation/corrective_run/**` are `-text`
  (stored and checked out byte-exact). `.gitignore`: staging leftovers. `make_zip.py --output`.
- `capture_inputs.py` runs the test suite without `test_packaging_integrity.py`, which checks the finalized bundle
  built afterwards from those inputs (its result is recorded below instead).

## Evidence

```text
python -m pytest code/tests/test_run_publication.py code/tests/test_packaging_integrity.py -q
19 passed                    (before finalization the packaging test failed 2/4 on the historical bundle:
                              no diagnostics hash / no evaluation_inputs — the old package is not a valid release)
python -m pytest code/tests -q
163 passed, 2 skipped        (0020: 144; +15 publication, +4 packaging)
git diff --check             (clean)
```

`test_run_publication.py`: injected validation and generation failures keep the selected output; a valid candidate
replaces it; a subset cannot target `output.csv`; the finalizer publishes a consistent bundle and refuses subset,
ablation, offline, wrong-revision, uncommitted-code, altered-output and missing-diagnostics candidates, and a report
failure, each leaving the previous bundle intact; a CRLF checkout (`core.autocrlf=true`, Git run with
`GIT_CONFIG_GLOBAL=/dev/null`, `GIT_CONFIG_NOSYSTEM=1`, no user setting touched) keeps the hashed bytes with the
attributes and converts them without (control).

Release (all at producing code `b90914b`, `uncommitted_producing_code: []`):

```text
python code/evaluation/capture_inputs.py            → evaluation_inputs.json at b90914b: sample default/ablation runs
                                                      (49 cached calls each, deterministic 0), custom 9/9,
                                                      discovery 77/111, tests 159 passed / metamorphic 4 passed
python code/main.py --cases all --no-cache --out runs/corrective/0021_candidate.csv --run-manifest-output runs/corrective/0021_candidate.manifest.json
  run 0021_candidate_20261025T104010Z, 518 rows, validation 0 errors / 105 warnings, published, exit 0
  535 live calls: Jev intent 518 + category fallback 3, Gemini vision 11, Azure adjudication 3;
  273,276 input / 92,347 output tokens; estimated $0.2403 (unverified third-party prices)
validator(candidate, its diagnostics)               → 0 errors, 105 warnings
python code/tools/finalize_run.py --candidate-manifest … --evaluation-inputs …   → exit 0
  output.csv sha256 81b317844674c62981d43b3c6eb575fc30520737d5e32078de3ea9a86e9e0ecb
validator(output.csv, final_run/diagnostics.jsonl)  → 0 errors, 105 warnings
python code/evaluation/make_reports.py              → both reports byte-identical to the finalizer's
python code/tools/make_zip.py                       → 271 files, 443,607 bytes, secret scan clean
                                                      (no dataset/, .env, caches, runs/, __pycache__; .env.example is a template)
```

Clean room (`test_packaging_integrity.py`): archive extracted + dataset + output.csv only → reports rebuild
byte-identically with provider credentials removed; `main.py --cases sample --offline` exits 0 with 32 rows.

Corrected output vs the overnight output (518 rows): INCOMPLETE 459 / COMPLETE 49 / NOT_APPLICABLE 10 (was 461/47/10);
4 rows differ: case_86 and case_390 INCOMPLETE → COMPLETE (spec 0017: a later NOT_FOUND read of the same copy
supersedes an earlier FOUND); case_33 export_1260 now ABSENT (0017: a later full primary snapshot omits it; still
INCOMPLETE); case_61 EMPTY_OBLIGATIONS → UNKNOWN_STATE (the live Jev category fallback now maps `object_19` to
SECONDARY_IDENTIFIER at p ≥ 0.5; still INCOMPLETE). The 105 warnings are INCOMPLETE cases whose blocker flag explains
the missing finding: ACCOUNT_UNGROUNDED 342 cases overall, UNKNOWN_STATE 3, REQUIRED_RECORD_MISSING 1 (case_34's
retained audit record is absent; no operation can restore it). Grounded accounts 166 / ungrounded 342.

## Scorer snapshot

Sample runs use the same cached provider responses (from this pass's live sample run).

| When / split | Code revision / configuration | Status accuracy | Account linkage / coverage | Step F1 | Sequence exact |
|---|---|---|---|---|---|
| Before / dev | `6907176` (0020), cached responses | 0.750 (15/20) | 7/20 correct, 13 ungrounded | 0.900 | 0.250 (5/20) |
| Before / all samples | `6907176` (0020), cached responses | 0.719 (23/32) | 12/32 correct, 20 ungrounded | 0.896 | 0.281 (9/32) |
| After / dev | `b90914b`, cached responses | 0.750 (15/20) | 7/20 correct, 13 ungrounded | 0.900 | 0.250 (5/20) |
| After / all samples | `b90914b`, cached responses | 0.719 (23/32) | 12/32 correct, 20 ungrounded | 0.896 | 0.281 (9/32) |

## Release and publication evidence

- Remaining limitations: 342/508 deletion requests have no grounded account link (INCOMPLETE by contract); the 0010
  ≥85% discovery target is unmet (77/111); model answers at bounded points vary between live runs (case_61); prices
  are unverified estimates; samples are an inspected regression set, not hidden-answer accuracy.
- Known provenance caveat: `main.py` reads the Git revision when it writes the manifest, so a commit during a run
  would mislabel it. During this run HEAD stayed at `b90914b` (the bundle commit `67bb114` was pushed with
  `git commit-tree` without moving HEAD and fast-forwarded only after the run).
- `code.zip` and `agent-trace.zip` are gitignored build outputs: rebuild them from the final commit before upload.
  Nothing was submitted.
