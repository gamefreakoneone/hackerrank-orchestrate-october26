# Spec 0021 — Validated final run and packaging: requirements

**Status:** Not started. **Depends on:** 0020.

## Goal

Produce and publish a corrected final run whose output, proof diagnostics, reports, usage and package agree.

## Acceptance criteria

- Candidate generation/validation must complete before replacing an existing selected output. Failed
  generation, failed validation or interrupted candidate writing must leave the previous selected CSV intact.
- Publish only the default pipeline as the selected output. Keep samples, custom fixtures and ranked-account
  or trust-claims ablations separate; no configuration is selected merely because it has more COMPLETE rows.
- Record the actual producing code revision, input/configuration identities, run ID and output checksum. Do
  not replace the producing revision with a later documentation-only commit or select a manifest by mtime alone.
- Produce exactly 518 unique, ordered request rows with valid steps and eligible citations. Run the validator
  with the matching diagnostics, and explain remaining blockers/warnings rather than labelling them successes.
- The selected output, diagnostics, final-run manifest, usage ledger, evaluation inputs and reports form one
  validated bundle. Missing, stale or mismatched required artifacts prevent ready status.
- Byte-hashed release artifacts must retain their declared bytes across supported checkout platforms. Test
  LF/CRLF handling; do not silently weaken checksum validation or regenerate predictions to fix checkout conversion.
- Rebuild code.zip from the validated tree; inspect required reports/README and exclusions. Verify the runnable
  extracted layout, focused offline checks and report rebuilding without the developer's ignored artifacts.
- Update MORNING_REPORT, SUBMISSION_CHECKLIST and interview notes with actual corrected metrics, provenance,
  limitations, artifact locations and publication status. Do not infer a deadline or submit automatically.
- Commit and push the completed spec, verify publication, and include the actual harness trace checkpoint.

## Boundaries

Use existing runners, serializers, validators, report and packaging functions. A thin finalization command is
allowed to prevent manual mismatches; no new workflow framework, deployment system or storage service is needed.
