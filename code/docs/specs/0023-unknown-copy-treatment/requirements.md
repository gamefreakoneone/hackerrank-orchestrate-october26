# Spec 0023 — Unknown copy treatment: requirements

**Status:** Not started. **Depends on:** 0022.
Read review M1 and the 0017/0018 per-copy/preservation contracts.

## Confirmed defect

`current_state_by_physical_copy()` constructs DISABLED/BLOCKED states from treatment facts only. A known-present
replica with no enabled/restore_allowed fact disappears when another copy is proven compliant. Isolated baseline
counterexamples return satisfied=True and COMPLETE for both DATA_FLOW and BACKUP_ARCHIVE.

## Acceptance criteria

- Account for every relevant identified copy when evaluating DISABLED and BLOCKED. Known presence without an
  establishing treatment fact is UNKNOWN, not an omitted copy or implied compliance.
- Any unresolved required copy prevents satisfaction/COMPLETE. A known violation in another copy must still
  produce its supported finding/remediation; unknown treatment alone must not invent an ACTIVE finding.
- Preserve per-copy state/proof diagnostics, including why treatment is unknown. A presence proof is not a
  disabled-flow or blocked-restore proof.
- Preserve 0018: a later same-copy absence may remove a flow risk, but a retained archive missing everywhere
  remains REQUIRED_RECORD_MISSING. A retained compliant copy does not clear an unchecked other copy.
- A later supported treatment fact for the unknown copy can resolve it; a post-cutoff fact cannot.
- Integrate uncertainty with existing completion blockers, planner and validator. Keep output operations/fields
  unchanged and future verification evidence empty for INCOMPLETE cases.
- Add meaningful regressions for both process and retained-backup paths, compliant resolution, absent copies and
  a known violation alongside an unknown copy. Measure actual dataset impact separately from synthetic results.

## Boundaries

Use the existing ResourceState, CopyState and obligation pipeline. Extend internal diagnostics only as needed;
do not introduce a parallel state model or infer a disabled process from missing fields.
