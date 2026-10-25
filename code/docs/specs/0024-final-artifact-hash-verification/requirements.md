# Spec 0024 — Final artifact hash verification: requirements

**Status:** Not started. **Depends on:** 0023.
Read review M2 and spec 0020's reproducibility requirements.

## Confirmed defect

`make_reports.load_final_run()` checks the selected output hash but merely checks existence/case coverage for final
diagnostics and existence for the usage ledger. It accepts valid JSON with altered flags or token counts even when
the manifest's diagnostics_sha256 / usage_ledger_sha256 disagree.

## Acceptance criteria

- Verify raw bytes against every required final artifact hash before interpreting diagnostics, token usage or
  rendering reports: output, diagnostics and usage ledger.
- Missing required hashes, missing files, malformed declarations and mismatches fail explicitly with the artifact
  role/path. Do not normalize line endings to make a mismatch pass or silently accept legacy incomplete manifests.
- Reuse existing SHA-256/artifact verification helpers; keep one behavior across report loading and finalization.
- A rejected input leaves selected reports and any pre-existing staging output unchanged. Validate required inputs
  before creating/replacing rendered reports.
- Test altered-but-parseable diagnostics with unchanged case coverage and altered-but-parseable token counts;
  missing-hash cases must fail too. Test the real report CLI, not only a fixture's expected exception.
- The intact preserved bundle still rebuilds byte-identically without model calls. Keep usage totals derived from
  the verified ledger and retain same-revision/configuration checks for evaluation inputs.
- Update fictional test manifests to contain genuine hashes of fixture bytes. Do not bypass integrity checks to
  keep old tests passing.

## Boundaries

This spec closes the confirmed unchecked-hash path. Broader historical narrative provenance, signatures, a new
manifest framework and pricing research are outside scope. Record other confirmed issues separately.
