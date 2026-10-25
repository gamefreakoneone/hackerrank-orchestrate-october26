# Spec 0024 — Final artifact hash verification: design

## Owned behavior

`code/evaluation/make_reports.py:load_final_run`, its existing verified_artifact helper, direct finalizer callers,
`code/tests/test_report_reproducibility.py`, and affected publication/packaging fixtures.

1. Resolve each required artifact from the selected manifest using the existing repository-relative convention.
   Require a valid expected digest and verify bytes before parsing any of that artifact's contents.
2. Preserve the output hash, case-coverage and revision checks already present. Use role-specific explicit errors
   for diagnostics/ledger mismatches and missing required declarations rather than accidental KeyErrors.
3. Reuse `sha256_of` and the existing artifact verifier; extend the helper only if its current interface cannot
   serve both callers. Do not add a second checksum implementation.
4. Keep report loading model-free and side-effect-free. The report CLI should finish all required validation before
   writing either report; a wrong ledger must not leave an updated evaluation report beside an old usage report.
5. Update fixture manifests with actual diagnostics/ledger digests. Include a positive fixture that proves changed
   legitimate ledger bytes plus a correctly refreshed manifest are accepted and reflected in the report.

## Regression reproductions

The audit used the actual baseline load_final_run function with memory-backed paths. It changed one diagnostics
row's flags while preserving all case IDs, then separately increased one ledger row's input_tokens by 123456.
Both hashes no longer matched their declared values; both loads succeeded. The committed artifacts themselves
matched all three hashes — this is a loader defect, not evidence that the release was tampered with.

Extend the existing report tests with equivalent temporary-file mutations and run the CLI with provider credentials
removed. Assert nonzero exit, the relevant role in the error, and unchanged pre-existing report bytes. Also cover
missing hashes and CRLF byte changes without treating line-ending conversion as harmless.

No sample prediction change is expected. Record before/after scorer results rather than filling in an expectation
as a measurement. Record the model-free preserved-bundle rebuild separately from offline inference metrics.
