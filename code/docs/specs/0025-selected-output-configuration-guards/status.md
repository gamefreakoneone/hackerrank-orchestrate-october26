# Spec 0025 — Selected-output configuration guards: status

**Status:** Completed (implementation). Release regeneration: **pending** — the preserved b90914b output still carries
the 0022 temporal defect in case_135/case_383 and is not relabelled as produced by the corrected code.
**Depends on:** 0024 — completed and pushed as `259b1422cc1fe783dba1bf66ce7d02278bdc2920` on
`claude/specs-0017-0021-5s3kpe` (remote verified before this spec started).
**Working/push branch:** `claude/specs-0017-0021-5s3kpe`
**Implementation/publication:** committed as `spec 0025: guard selected output from non-release runs`; its pushed SHA is
recorded in the session's final report.

## What changed

- `ghostaudit/provenance.release_configuration_violations(run_args)`: the one release-configuration predicate
  (`--cases all`, `--case` absent — an explicitly empty selector also counts —, no ablation,
  `--ungrounded-account-steps none`, not offline; `--no-cache` is a cache policy and allowed). Two real callers.
- `main.py`: `refuse_non_release_run_targeting_selected_output` runs right after argument parsing, before data
  loading, provider/ledger creation or staging. It compares resolved paths (aliases such as `./output.csv` or
  `../repo/output.csv` are caught; a scratch file named `output.csv` is not) and adds the CLI-only check that
  `--data-root` resolves to the canonical `dataset/`. The old `--case`-only guard is deleted.
- `tools/finalize_run.py`: the candidate's declared arguments go through the same predicate (now also refusing
  `--cases sample` and empty selectors); coverage/hash/validation checks unchanged; no machine-path data-root check.
- `code/README.md`: safe sample/offline commands, the selected-path contract and the refusal message.

## Regression evidence

`code/tests/test_run_publication.py` with an isolated selected-path fixture (`main.SELECTED_OUTPUT` relocated; a spy
replaces `load_dataset` and `LLMLayer` and fails if inference starts): sample, `--case case_01`, empty `--case`,
both ablations, ranked accounts, offline and a custom data root are each refused through three path aliases, leaving
the fixture output and diagnostics bytes unchanged and creating no file. Positive: the existing alternate-destination
offline sample runs still publish; a release-configuration run publishes to the (fixture) selected path with only the
provider boundary swapped for the cache-only layer (test-only fixture manifest, no claim of a live run). Finalizer:
declared sample, empty-selector, subset, ranked, ablation and offline candidates are refused, previous bundle intact.

On the 0024 code 15 publication tests failed: 8 selected-output refusals (the old guard refused only a nonempty
`--case`), the release-publication test (no canonical data-root concept), and 6 finalizer cases — of which declared
`--cases sample` and empty `--case []` were genuinely accepted; subset/ranked/ablation/offline were refused before but
with the older message. All pass after. The real root `output.csv` hash (81b31784…) was checked before and after.

## Scorer snapshot

| When / split | Revision / configuration | Status accuracy | Account linkage | Step F1 | Sequence exact |
|---|---|---|---|---|---|
| Before / dev | `259b142`, `run_eval.py --split all -- --offline --no-cache` | 0.750 (15/20) | 0.350 (7/20) | 0.899 | 0.250 (5/20) |
| After / dev | this change, same configuration | 0.750 (15/20) | 0.350 (7/20) | 0.899 | 0.250 (5/20) |

No prediction code changed; sample outputs byte-identical.

## Checks

- `python -m pytest code/tests/test_run_publication.py code/tests/test_packaging_integrity.py -q`: 30 passed.
- `python -m pytest code/tests -q` (RUN_LIVE unset, settled code): 197 passed, 2 skipped (Linux).
- `python code/evaluation/make_reports.py --report-output-directory runs/corrective/0025_rebuilt`: both reports
  byte-identical to the selected ones.
- `python code/tools/make_zip.py --output runs/corrective/0025_code.zip`: 291 files, 493,159 bytes, secret scan clean;
  contains README.md, main.py, both evaluation reports and the new test files; no dataset/, caches or traces. It holds
  corrected code beside the **historical** b90914b reports — a packaging check, not a refreshed submission.
- `git diff --check`: clean.

## Release readiness

Corrected code: complete for 0022–0025. Release artifacts (`output.csv`, `final_run/`, `corrective_run/`, reports):
still the historical b90914b bundle — regeneration needs the full live procedure in `code/README.md` and explicit
permission. Nothing was submitted.
