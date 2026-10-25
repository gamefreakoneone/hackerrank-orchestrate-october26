# Independent implementation review

- Reviewed revision: `2a722566e1367f409a5b3789ce61c1c19c566cfc`, branch `claude/nifty-tesla-4ig5f5`.
- Recorded: 2026-10-25; review performed read-only in this OpenCode session, model `azure/gpt-6-astra`.
- Scope: core implementation, overnight/evaluation reports, output, final-run diagnostics/manifest/usage ledger.
  The source was inspected remotely because the local branch still held the planning revision.
- File/line references below identify the reviewed revision, not future corrective implementations.

## Summary

A real terminal-runnable pipeline and submission-shaped artifacts exist. It resolves identity, parses evidence,
uses typed AI results, reconstructs state, applies policy and emits plans. Completion of the implementation
milestones does not establish full audit correctness. Two code defects were reproduced, and discovery/report
limitations remain. Specs 0017–0021 address these findings without restarting Phase 0.

## Independently verified artifacts

The review downloaded the pinned output, diagnostics, manifest and ledger into memory. It checked row coverage,
uniqueness, numeric ordering, step structure and file-citation cutoffs against participant CSVs. The actual
validator and selected inspected source functions were exercised in memory; no live providers were called.

| Check | Verified result |
|---|---|
| Output | 518 unique rows covering the request file; 47 COMPLETE, 461 INCOMPLETE, 10 NOT_APPLICABLE |
| Output SHA-256 | `09c8ecf6781e295799866b3e875c21f456de240f8d0b31f4b960a8f59ac786e3`, matching the manifest |
| Step count | 2,698: 724 findings, 724 remediation steps, 1,250 verifications |
| Grounded accounts | 166 of 508 deletion requests; 342 ungrounded |
| Validator with saved diagnostics | 0 errors, 104 warnings (INCOMPLETE outputs without findings) |
| Validator without diagnostics | 104 errors, 0 warnings |
| Ledger | 535 noncached rows: Jev 521, Gemini 11, Azure 3; 273,276 input and 88,704 output tokens |

The sample figures **23/32 status, 12/32 account linkage, step F1 0.898, and 9/32 exact sequences** are the
overnight report's results, not a fresh end-to-end replay by this reviewer. Their scorer definitions were checked.
Custom-test and full-suite success claims were not independently rerun. Recorded token sums were verified;
provider billing and the report's third-party price estimates were not independently verified.

INCOMPLETE includes inability to prove completion, not just demonstrated leftover data. The 104 outputs without
findings depend on explicit diagnostic blockers. No untouched holdout or hidden-answer accuracy is available.

## Findings

### 1. New primary evidence can erase an uncleared replica from the decision

References: `code/ghostaudit/timeline.py:105-115`, `code/ghostaudit/timeline.py:164-179`,
`code/ghostaudit/obligations.py:23-41`.

The latest-file selector is global; its any-copy preference is limited to one chosen capture/file. Reproduced:

- An older failover replica contains the subject's email; a newer primary-only 404 causes COMPLETE/ABSENT.
- An older replica exposes PII; a newer clean primary causes COMPLETE/REDACTED.

Correct per-copy state and treatment aggregation, including the evidence used to clear each copy (0017).
These isolated counterexamples establish a code defect; they do not identify which saved COMPLETE rows are affected.

### 2. Absence satisfies treatments that require preservation

References: `code/ghostaudit/obligations.py:45-61`, `code/ghostaudit/planner.py:35-38`.

The satisfying-state table accepts ABSENT for REDACTED/ANONYMIZED/BLOCKED. Reproduced a missing account tombstone
accepted as COMPLETE with VERIFY_RECORD_REDACTED and a missing retained backup accepted as COMPLETE with
VERIFY_RESTORE_BLOCKED. Required presence must be checked independently of treatment (0018).
No such satisfied absent/non-DELETE obligation was found in the saved final diagnostics.

### 3. Coverage remains an explicit acceptance gap

References: `code/docs/specs/0010-discovery-and-state/status.md:3-4`,
`code/docs/specs/0010-discovery-and-state/status.md:24-47`;
`code/evaluation/evaluation_report.md`.

0010 was marked Completed although its reported resource recall is 77/111, below the ≥85% target. The reported
12/32 correctly linked current accounts imply 100% precision on selected links, not complete coverage. Preserve
the grounding requirement; investigate and measure any justified improvement without promising one (0019).

### 4. Report claims and reproduction need correction

References: `code/evaluation/make_reports.py:139-151`, `code/tools/state_report.py:49-66`,
`code/ghostaudit/validate.py:182-192`, `code/docs/SUBMISSION_CHECKLIST.md:12`.

- The hardcoded sentence that every grounded sample has an exact plan contradicts 12 grounded cases and nine
  exact plans. Claims must be derived from per-case measurements.
- The 104/111 state and 75/75 citation results supply gold resource IDs and expected operations to the state
  checker. Label them oracle-assisted component diagnostics, not end-to-end discovery success.
- The README/checklist validator command omits required diagnostics and reproduces 104 errors. Append
  `--diagnostics code/evaluation/final_run/diagnostics.jsonl` for the preserved selected output.
- `make_reports.py` reads sample/ablation inputs under ignored `runs/`; preserve the necessary inputs and manifest
  relationships or document a reproducible generation path. Rebuilding reports should not need new model calls.

Spec 0020 owns reporting and reproducibility. Preserve historical results with their actual provenance.

### 5. Release publication must preserve a previous valid result

References: `code/main.py:73-88`, `code/ghostaudit/serialize.py:23-29`.

The current CLI writes the destination before validation. Candidate-first validation/promotion is required by
the approved correction plan (0021), with matching code, diagnostics, reports and usage artifacts. The original
output is a preserved checkpoint, not evidence that future failed runs cannot overwrite it.

### Post-sync observation — checked-out artifact bytes

During preparation of this handoff, the fast-forwarded Windows checkout converted root output.csv line endings.
The committed blob still hashes to `09c8ecf6781e295799866b3e875c21f456de240f8d0b31f4b960a8f59ac786e3` and matches
the manifest. The working file hashes to `00ae31e21f991810784df4fca0ba6cb765cf12bf9a35054b989ca33ce9f6fc3c`;
the two differ only by LF/CRLF normalization. This was verified after syncing, not in the earlier remote audit.
No output edit is included in the documentation commit. Spec 0021 must preserve byte-hashed release artifacts
across checkout rather than silently bypassing checksum verification or rerunning models to repair line endings.

## Priority and handover

1. 0017: per-copy state and proof correctness.
2. 0018: required record preservation.
3. 0019: bounded grounded-discovery improvement and coverage accounting.
4. 0020: truthful, reproducible evaluation/reporting.
5. 0021: final-run integrity and packaging.

Use `code/docs/CORRECTIVE_HANDOFF.md`. Do not infer a deadline, fabricate metrics or submit automatically.
