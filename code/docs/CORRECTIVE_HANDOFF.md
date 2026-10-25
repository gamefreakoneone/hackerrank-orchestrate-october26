# Corrective implementation handoff — specs 0017–0021

> Historical handoff for the completed first correction pass. For current work, read
> [CORRECTIVE_HANDOFF_0022_0025.md](CORRECTIVE_HANDOFF_0022_0025.md) and
> [review 0002](reviews/0002-corrective-pass-review.md). Continue on `claude/specs-0017-0021-5s3kpe` with spec 0022;
> the original kickoff below is preserved as history, not an instruction to return to the old baseline.

The overnight implementation at `2a722566e1367f409a5b3789ce61c1c19c566cfc` has been fast-forwarded into
`claude/eager-cray-7fhtkf`. The initial audit is `reviews/0001-implementation-review.md`.
This document and the five specs are a **documentation handoff**: their corrections are not implemented yet.
Use this prompt for the next Claude Code implementation session, replacing the old overnight kickoff.

## Copy-paste prompt

```text
Inspect the working tree and preserve unrelated changes. In a clean checkout, fetch origin,
check out claude/eager-cray-7fhtkf, and fast-forward it from origin before editing.
Do not reset or force-push. If the cloud session forces another branch, declare the actual
working/push branch in the log and reports; ensure it contains the corrective spec commit.

Read AGENTS.md, CLAUDE.md, code/docs/FEATURE_STATUS.md,
code/docs/reviews/0001-implementation-review.md, and code/docs/CORRECTIVE_HANDOFF.md.
Then implement specs 0017 through 0021 in order, starting with the next Not started spec.
Read all four files of each spec before coding and satisfy its dependencies.
Phase 0 and the original overnight run are historical; do not restart them.

Apply YAGNI, DRY after the second duplication, explicit failures, simple solutions first,
verified deletion of superseded code, and verbose semantic naming. Preserve strict cutoffs,
grounded-only normal output, required retained records, and the supplied output schema.
Do not change sample answers, invent proof, add speculative frameworks, or guess links to
improve a score. Insufficient evidence must remain an explicit audit blocker.

Capture comparable before/after sample measurements and regression evidence for every spec.
Distinguish rerun measurements from the historical report. Keep correctness-required changes
even if a sample metric decreases; document why. An unpassed mandatory check means Blocked.

After each spec: update status.md, tasks.md, FEATURE_STATUS.md and the morning report;
append the log with actual runtime tool/model identifiers; export and verify the real session
trace; commit that spec; PUSH and verify the remote contains the commit BEFORE starting the
next spec. Preserve a local commit on push failure and resolve the publication blocker safely.
Never call local-only work saved remotely. Only one agent should write the branch at a time.

Use samples and focused tests during development. Do the full 518-case final run in 0021.
Preserve the old selected output until a candidate and its matching artifacts are validated.
Keep ranked-link ablations separate from the selected default output. Do not submit automatically.

Finish with actual commit SHAs and push branches, checks run, measured results, unresolved
limitations, selected-output provenance, and artifact readiness. If blocked, state precisely
what failed and the next action rather than reporting completion.
```

## Baselines and validation discipline

- Historical sample results at `2a72256`: status 23/32, current-account linkage 12/32, step F1 0.898,
  sequence exact 9/32. These are **reported**, not new measurements. The review independently checked
  the saved full-output checksum/counts, ledger totals and specific function counterexamples.
- Preserve root `output.csv` and `code/evaluation/final_run/` while correcting the engine. The saved
  full-output SHA is `09c8ecf6781e295799866b3e875c21f456de240f8d0b31f4b960a8f59ac786e3`.
  This is the committed blob's hash. The Windows checkout currently applies CRLF normalization and has a
  different working-file hash; see the review's post-sync observation. Spec 0021 owns byte-stable artifact
  storage/publication. Do not hide the mismatch or spend a model run merely to reproduce committed bytes.
- Run before/after samples using the same provider/cache configuration and inputs. Record code revision,
  provider availability and whether cached vision data exists. An offline run without PNG facts is a
  different configuration, not an unexplained regression against the live baseline.
- Each `tasks.md` lists exact commands. Test files/CLI options marked **planned** must be implemented by
  that spec. `RUN_LIVE` stays unset for offline unit tests. Missing prerequisites are recorded, not installed
  or bypassed silently; pin any justified new dependency in the same spec.
- Use existing evaluators. The sample runner writes `<output-stem>.diagnostics.jsonl`; pass that matching
  diagnostics file when scoring or validating. A schema-valid file does not establish hidden-answer accuracy.
- Status tables retain `not measured` until a command actually runs. Use `runs/corrective/` for intermediate
  outputs, never the selected root output. In 0020, preserve release evaluation inputs for 0021 to publish.
- Commit/push an In progress code-freeze checkpoint if needed to identify the code that produces the final
  run. This is not a Completed spec; final checks/artifacts and the completion commit still follow.
- Update `MORNING_REPORT.md` after each spec with current correction progress. Keep the old overnight
  measurements explicitly historical, and do not rewrite them as if the corrected code produced them.

## Exit criteria

All five specs' acceptance checks pass, their evidence and actual publication references are recorded, and
0021's selected output/manifest/diagnostics/usage/reports/package are consistent. If investigation in 0019
finds no additional justified links, documented unchanged coverage is allowed; fabricated improvement is not.
No broader rewrite or optional optimization is required. The final answer must name the actual push branch.
