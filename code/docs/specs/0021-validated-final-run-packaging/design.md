# Spec 0021 — Validated final run and packaging: design

## Safe output publication

`main.py` currently writes the destination before validation. Stage candidate bytes beside the destination,
finish the relevant diagnostics/manifest, validate against the intended request set, then replace the selected
CSV only after success. Prefer straightforward `Path`/`os.replace` behavior, with cleanup limited to temporary
files owned by this run. A caller must never receive exit 0 for a failed validation. Preserve partial-run
semantics explicitly; a `--case` subset is not a valid replacement for the full submission.

The reviewed Windows checkout normalizes the committed output CSV to CRLF, invalidating its byte hash. Prefer
a narrow Git artifact-storage rule (for example, appropriate `.gitattributes` entries for the hashed release
paths) and consistent writer bytes over a new conversion framework. Verify a clean checkout's artifact hash;
do not define a different checksum calculation silently or conceal a real content mismatch.

Add `--run-manifest-output PATH` (planned) so a release can identify its manifest without guessing the newest
file in `runs/`. Preserve existing defaults/callers. Use a name such as `run_manifest_output_path` internally.

Use a thin `code/tools/finalize_run.py` (planned) accepting `--candidate-manifest PATH` and
`--evaluation-inputs PATH`. Reuse the existing validator, hash checks, 0020 report functions and packaging
conventions. It must:
1. validate the candidate, diagnostics, usage ledger, producing revision/configuration and evaluation inputs;
2. stage the selected-run files and reports, resolving all artifact references from the manifest, not globals;
3. preserve the previous selected bundle until staging/validation succeeds;
4. publish the selected output and tracked `code/evaluation/final_run/` artifacts with relative, reproducible
   paths and recheck consistency; on an interrupted publication, fail visibly with a recoverable run identity
   rather than reporting the bundle ready. Do not claim a multi-file operation is atomic if it is not.

No inference is rerun inside finalization or report rebuilding. The next Git checkpoint records a consistent
bundle; the previously committed release remains the recovery point. Update README with the exact procedure.

## Code freeze, tests and artifacts

- Commit/push an **In progress** runtime checkpoint if source changes in this spec need a producing revision
  before the full run. Record its actual SHA. Do not mark 0021 Completed at that checkpoint.
- Refresh the sample/ablation/custom input bundle through 0020's workflow using this producing code and recorded
  modes, then run the final full dataset once cold-cache. Repeated model runs require a new failure/change reason.
- Add `code/tests/test_run_publication.py` (planned): injected generation/validation/report-staging failures keep
  the old selected output; valid promotion succeeds; subset, wrong-code/config, wrong-hash and missing-diagnostics
   candidates are refused; fake providers keep these tests offline.
- Include a checkout/line-ending regression for the byte-hashed artifact contract, documenting how the test
  controls Git configuration without changing the user's global Git settings.
- Add `code/tests/test_packaging_integrity.py` (planned) only for meaningful archive/rebuild coverage not already
  tested: correct extracted layout, required reports, excluded dataset/secrets/caches, manifest consistency and
  offline report rebuilding. The old package's existence must not be mistaken for a successful new build.
- Keep original measured data labelled with its producing revision. A later report/doc-only commit may package
  the unchanged producing code, but must not mislabel the source of predictions or token usage.
