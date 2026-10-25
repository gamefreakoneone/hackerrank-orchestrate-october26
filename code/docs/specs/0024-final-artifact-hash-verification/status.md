# Spec 0024 — Final artifact hash verification: status

**Status:** Completed
**Depends on:** 0023 — completed and pushed as `acf3b3a8c2dbaec60a818faf6f1f8a04996877af` on
`claude/specs-0017-0021-5s3kpe` (remote verified before this spec started).
**Working/push branch:** `claude/specs-0017-0021-5s3kpe`
**Implementation/publication:** committed as `spec 0024: verify every final artifact hash`; its pushed SHA is recorded
in the next spec's status / final report.

## What changed

- `make_reports.verified_artifact` now also rejects a missing/malformed declared digest (must be 64 lowercase hex)
  with the artifact role in the error; raw bytes are compared, no line-ending normalization.
- `make_reports.load_final_run` verifies output, diagnostics and usage ledger through that helper before parsing any
  of them; missing path/hash declarations fail explicitly (no KeyError). Case-coverage check retained.
- `make_reports.main` renders both reports before writing either, so no failure can leave a new evaluation report
  beside an old usage report.
- `tools/finalize_run.py` uses the same helper for candidate files (one checksum behavior) and drops its separate
  post-publication diagnostics/ledger hash loop, which `load_final_run` now covers.
- `code/README.md` integrity wording updated. Revision/configuration checks for evaluation inputs unchanged.

## Regression evidence

`code/tests/test_report_reproducibility.py`: the fixture manifest now carries genuine digests of its fixture bytes.
New real-CLI tests (fresh process, no credentials, unusable proxy): altered-but-parseable diagnostics flags (same
case ids), ledger `input_tokens` +123456, ledger converted to CRLF, missing output/diagnostics/ledger hash, malformed
(uppercase) hash — each exits 1 naming the role and leaves pre-existing staged report bytes unchanged; a refreshed
ledger with its refreshed hash is accepted and its token total (124690) appears in the usage report. On the baseline
code 8 report tests failed (the 7 rejection cases plus the altered-output test, whose message now comes from the
shared verifier); all pass after.

Preserved-bundle rebuild (model-free, separate directory; selected reports not overwritten):

```text
$ python code/evaluation/make_reports.py --report-output-directory runs/corrective/0024_rebuilt
$ cmp code/evaluation/evaluation_report.md runs/corrective/0024_rebuilt/evaluation_report.md   # identical, 9218 bytes
$ cmp code/evaluation/usage_report.md runs/corrective/0024_rebuilt/usage_report.md             # identical, 2560 bytes
```

Selected artifact hashes unchanged: output 81b31784…, diagnostics ae42396f…, ledger 445a8b5b….

## Scorer snapshot

| When / split | Revision / configuration | Status accuracy | Account linkage | Step F1 | Sequence exact |
|---|---|---|---|---|---|
| Before / dev | `acf3b3a`, `run_eval.py --split all -- --offline --no-cache` | 0.750 (15/20) | 0.350 (7/20) | 0.899 | 0.250 (5/20) |
| After / dev | this change, same configuration | 0.750 (15/20) | 0.350 (7/20) | 0.899 | 0.250 (5/20) |

No prediction code changed; sample outputs byte-identical.

## Checks

- `python -m pytest code/tests/test_report_reproducibility.py code/tests/test_run_publication.py
  code/tests/test_packaging_integrity.py -q` (Linux): 38 passed.
- `python -m pytest code/tests -q` (RUN_LIVE unset): 186 passed, 2 skipped.
- `git diff --check`: clean.
