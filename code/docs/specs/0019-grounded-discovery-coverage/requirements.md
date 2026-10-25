# Spec 0019 — Grounded discovery coverage: requirements

**Status:** Completed (investigation only). **Depends on:** 0018.

## Goal

Improve evidence-backed discovery where possible and measure the remaining gap honestly.

## Acceptance criteria

- Re-measure sample current/historical account linkage, resource recall, extras, precision and provenance
  under the corrected engine and a documented provider/cache configuration.
- Classify missing sample resources as missing eligible evidence, ambiguous identity linkage, or an actual
  parser/reference-discovery limitation. Separate oracle-assisted investigation from pipeline predictions.
- Examine actual pre-cutoff identifier/reference fields and existing PNG observations. Add a rule only when
  the data supports a general relationship; include decoy and cutoff regression tests for any added rule.
- Every new grounded link has inspectable file/record/trace/reference provenance. Exclude post-cutoff values;
  timing proximity, case families, numeric IDs and prefix uniqueness do not establish ownership.
- Keep unsupported candidates in diagnostics. Preserve historical grounded accounts unless evidence excludes
  them. Measure false links as well as hits; increasing recall alone is not success.
- An investigation-only outcome is acceptable if no additional defensible links are found: record searches,
  evidence and unchanged metrics. Do not write a speculative feature to satisfy a numerical target.
- Report the old 0010 ≥85% target as unmet where still unmet; do not silently redefine it as achieved.

## Boundaries

Reuse existing parsing, discovery and evaluation tools. No new matching framework, provider or fuzzy identity
resolver is required. Do not edit dataset files or use golden labels inside the prediction pipeline.
