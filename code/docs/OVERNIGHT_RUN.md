# OVERNIGHT_RUN — unattended execution brief (post Phase 0d)

This run is **unattended**. The user will read `code/docs/MORNING_REPORT.md` in the morning.
Resolve routine implementation choices within the current contracts, record substantive decisions
in TECHNICAL_DESIGN.md → Decision log as `[overnight]`, and continue without asking questions.
An unavailable prerequisite is a blocker, not permission to invent evidence or passing checks.

If context is compacted, re-read this file, `CLAUDE.md`, `code/docs/FEATURE_STATUS.md`, the morning
report, and the current spec. Resume from recorded work; do not repeat completed paid runs.
The copy-paste kickoff prompt is in `code/docs/OVERNIGHT_KICKOFF.md`.

## 0. Authority and fixed decisions

- **Phase 0 is closed** at `bef2c66`, following phases 0, 0b, 0c and 0d and the review/correction
  history in FEATURE_STATUS.md. Focus on implementation, not another planning pass.
- AGENTS.md remains authoritative. Follow CLAUDE.md, TECHNICAL_DESIGN.md and the current specs.
  HANDOFF.md is historical where the recorded later decisions supersede it.
- Do not relax evidence or policy requirements to raise a sample score:
  - **Strict cutoff:** only information available at or before `audit_at` may influence discovery,
    identity, state, or citation. Exclude later identity snapshots and audit values.
  - **Grounded links:** an eligible record or trace must establish the subject identifier/account
    relationship. Identity matching and ambiguity checks use only identifiers available at that
    cutoff. Unresolved or ambiguous matching is not proof.
  - `ACCOUNT_UNGROUNDED` means INCOMPLETE with no account steps. Ranked guesses stay in diagnostics;
    only spec 0015's explicitly labelled ablation may emit them in INCOMPLETE output.
  - **Snapshot omission:** require eligible coverage under the current absence rule. Never restore
    discarded, pre-deletion snapshots as a fallback. An eligible direct readback can establish
    absence without snapshot omission. UNKNOWN applies when neither coverage nor another eligible
    observation establishes the state.
  - Keep older grounded accounts as historical obligations unless evidence excludes them.
  - Operational results such as `DELETE_RECORD SUCCESS` are claims. Apply the design's separate
    treatment of file observations and CHECK_DATA_FLOW / CHECK_RESTORE_ACCESS state-check fallback.
  - Preserve `POLICY_UNDEFINED` handling; do not invent inverse policy actions.
  - Report linkage accuracy separately from status accuracy. The earlier 23/32 bound is conditional
    on the current sample links, not measured pipeline accuracy or a dataset ceiling.
  - Samples are an inspected regression set; synthetic/metamorphic cases are custom validation.

## 1. Start and preflight

1. Read AGENTS.md. Inspect the branch and working tree before editing. Sync the clean checkout of
   `claude/eager-cray-7fhtkf` before appending logs. Do not discard unrelated changes. If sync is
   blocked, record the blocker and preserve the checkout rather than forcing it.
2. Follow AGENTS.md session logging with runtime-derived harness/model names. Log the actual kickoff
   prompt verbatim, with secrets redacted. Only one agent writes this branch during the run.
3. Read TECHNICAL_DESIGN.md, FEATURE_STATUS.md, all available files in `code/docs/reviews/`, and the
   subsequent 0b–0d decision-log entries. Do not assume a particular count of review files.
4. Read `agent_trace_instructions.md`, `problem_statement.md`, and AGENTS.md §6.8–6.9. Create
   `code/docs/SUBMISSION_CHECKLIST.md` with required artifacts, exact paths/formats, producing
   commands and current status. Create the initial morning report before expensive work.
5. Verify installed tools and required provider environment-variable names without printing values.
   Do not assume a new cloud session inherits a previous session's credentials or local `.env`.
   Record live smoke-test results separately from offline/fake-provider test results.
6. Record any user/platform-configured time, call or spend limits and reserve capacity for checkpoints
   and packaging. If a limit is unspecified, say so; do not invent a deadline or claim unlimited
   credits. Keep paid work to the bounded spec tasks and required retries, with no open-ended tuning.
   No live provider available means offline-capable work may continue where its actual acceptance
   criteria permit; it does not establish that AI extraction or live integration is working.

## 2. Execution order and grounded discovery

Follow CLAUDE.md's numeric order, skipping completed spec 0002:

```text
0001 → 0003 → 0004 → 0005 → 0006 → 0007 → 0008 → 0009
     → 0010 → 0011 → 0012 → 0013 → 0014 → 0015 → 0016
```

- 0001–0005: scaffold, loaders, serializer/validator, regression scorer and baseline.
- 0006–0009: identity, parsers, shared provider layer, and PNG extraction. This makes the provider
  layer available before spec 0011's category fallback and PNG evidence available for discovery.
- 0010–0013: discovery/state, policy, planner/citations, and intent. Until 0013, any keyword-only
  intent path must be explicitly identified as provisional in diagnostics and reports.
- 0014–0016: custom validation, final run/ablations/reports, packaging and interview notes.

Start a spec only when its prerequisites are Completed. If blocked, try the next numerically ordered
spec whose prerequisites are genuinely satisfied. Never complete a dependent spec using an absent
or silently stubbed prerequisite. Keep all mandatory acceptance checks; record unavailable live
capabilities separately rather than reporting them as successful.

### Spec 0010 priority: grounded account linkage

Measure improvements over the recorded baseline, using raw participant evidence and exact matching:

- **Readback logs:** extract complete `lookup_key` values and resource IDs from the same eligible
  record/trace. Apply the identity normalizations in spec 0006. The overnight-brief review found
  388 raw lookup keys with no literal ellipsis; all 50 account lookup lines matched a complete
  known email after case normalization (an all-dates structural check, not case eligibility).
  Shortened commentary excerpts are not truncated source evidence. Do not use prefix uniqueness
  as grounding; keep any partial matches as unresolved diagnostic candidates.
- **Service-export `profile_lookups`:** examine actual subject fields when `profile` is populated.
  Of 47 inspected entries, 37 had `profile=null`; their fields were `observed_at`, `profile`,
  `resource_id`, and `status_code`. A null profile/404 can prove state for an independently linked
  account, but does not supply the missing subject-to-account link.
- **Other diagnostic/delivery logs:** use identifier/resource relationships actually present in
  the record. Do not infer membership from file proximity or workflow timing.
- **Tombstones and references:** follow explicit eligible reference edges. A retained `user_id`
  without an account reference does not itself identify the deleted account.
- **PNG observations from 0009:** apply the same grounding and cutoff rules. Missing extraction is
  missing evidence, not evidence of absence. Measure the specified unreachable-resource checks.

Record unique-grounded, multi-grounded and ungrounded counts, linkage precision/recall, provenance,
and before/after sample metrics. Do not promote a candidate merely because it fits a sample answer.

## 3. Per-spec loop and output handling

For each eligible spec:
1. Read all four spec files and preserve its contracts.
2. Implement the spec; repair earlier components only when necessary and document the changes.
3. Run its exact validation commands and relevant tests. Once they pass, avoid redundant reruns
   unless a new change or unresolved concern requires them. Report failures and unavailable checks.
4. From 0005 onward, run the sample scorer and record before/after status, account-linkage, step and
   sequence metrics. Earlier measurements unavailable before the scorer exists are `not measured`,
   never fabricated numbers.
5. Update `status.md`, `tasks.md`, FEATURE_STATUS.md, the submission checklist and morning report.
   Mark Completed only when the spec's acceptance criteria are met.
6. Append the autonomous milestone log (§4), export and verify the trace, inspect the staged diff,
   then commit `spec NNNN: <summary>` and push. Record blocked attempts with an honest commit title.

Failure and regression handling:
- After three substantive repair attempts, mark the spec Blocked with failed commands and the
  missing prerequisite. Preserve the last validated checkpoint. Continue only with independent,
  eligible work; stop when none remains.
- Investigate every metric regression. Fix or revert accidental regressions. Keep changes required
  by the evidence/policy contract even when sample scores decrease, recording the reason and numbers.
- Do not erase unrelated work or use destructive resets to recover a checkpoint. If a push is
  rejected, reconcile remote work before retrying; preserve both sides of shared logs. If safe
  reconciliation is not possible unattended, record a publication blocker instead of force-pushing.

Output rules:
- Use sample outputs under `runs/` during development. Do not run all 518 cases after every spec.
- Specs 0001/0004 may write the required 518-row all-NOT_APPLICABLE scaffold baseline. Label it
  **format-only baseline**, not an audited or submission-ready result. Never overwrite a later
  audited checkpoint with this scaffold during testing.
- Use separate paths/run IDs for development, ablations and the final default pipeline. Preserve
  the final default run while ablations execute; a ranked-account ablation is never the final output.
- Spec 0015 produces the required cold-cache full run. Write a candidate, validate the complete CSV,
  then promote it to root `output.csv`; failed/partial writes must not replace the selected output.
- Record the selected run ID, producing code commit, configuration, output checksum, diagnostics and
  usage-ledger path. The evaluation/usage reports and packaged code must correspond to that output.
  File-format validity alone is not submission readiness; do not imply hidden-answer accuracy.

## 4. Logging and trace checkpoints

- Append the real user prompt once per actual user turn, per AGENTS.md §5.2.
- Extra progress entries must be labelled `spec NNNN completed (autonomous continuation)` or
  `spec NNNN blocked (autonomous continuation)`; identify them as continuations of the original
  prompt, not new user messages. Use actual write times and runtime-derived tool/model identifiers.
- Preserve old entries. Re-read newly appended metadata and verify exactly one populated `tool=`
  and `model=` line per entry. Never fabricate prompts, timestamps, test results or model usage.

Export the **actual harness** trace immediately before each commit, following CLAUDE.md and
`agent_trace_instructions.md`:

- **Claude Code:** `scripts/save_trace.sh` needs hook JSON on stdin. Obtain `SESSION_ID` and
  `TRANSCRIPT_PATH` from actual session metadata, then invoke it explicitly:

  ```bash
  jq -n --arg session_id "$SESSION_ID" --arg transcript_path "$TRANSCRIPT_PATH" \
    '{session_id:$session_id,transcript_path:$transcript_path}' | bash scripts/save_trace.sh
  test -s "agent-trace/claude-code/${SESSION_ID}.jsonl"
  ```

  Check that the file was refreshed and is parseable JSONL. The script always exits 0, including
  when metadata is missing; exit status alone is not evidence of a successful export.
- **Other harnesses:** use their documented session exporter and their own subfolder, e.g.
  `agent-trace/opencode/`. Do not fabricate Claude metadata or rely on its hook for another harness.
- Preserve structured session records and useful prompt/tool content while redacting secrets and
  private data. Inspect the exported file, not just the command result. If trace export is unavailable,
  record the exact blocker and never claim a complete trace.
- Include relevant trace changes and `log.txt` in the commit. Keep traces outside `code/`; the final
  trace archive is separate from `code.zip`. A pre-commit export is a checkpoint, not a claim to
  contain future messages after that export.

## 5. Hard rules and submission scope

- Predictions use only participant-facing `dataset/` evidence; no hardcoded labels, IDs or families.
  Participant-created fixtures remain isolated custom validation, not prediction shortcuts.
- Never read `sample_output.csv` inside the prediction pipeline. Code decides; models return typed facts.
- Read credentials from environment variables. Never print/commit secrets or edit AGENTS.md.
- Keep context lean with targeted reads and summarized scripts; avoid dumping entire evidence files.
- Package only the allowed solution/reports in `code.zip`. Produce the transcript/trace artifacts
  separately under the supplied submission rules.
- Do not infer a submission deadline from an announcement date. Record it only if an official source
  supplies it. The official challenge/submission page is:
  https://www.hackerrank.com/contests/hackerrank-orchestrate-october26/challenges/ghost-data-still-exists
- This run prepares artifacts and reports readiness; it does not submit automatically.

## 6. Stop conditions, morning report and wrap-up

Checkpoint after **every spec**, completed or blocked, and before an expensive run. Stop new work
when all specs are done, no dependency-eligible work remains, or an actual time/usage limit requires
wrap-up. Export/report before the limit is exhausted when possible; checkpoints protect against a
session that terminates before cleanup can run.

Keep `code/docs/MORNING_REPORT.md` current with:
- completed, blocked and not-started specs, failure reasons and existing commit SHAs; use the named
  pending commit for the current checkpoint and record its SHA in the next update;
- measured sample status accuracy, account-linkage accuracy/coverage, step F1 and sequence accuracy;
- output stage: **format-only baseline**, **audited pipeline checkpoint**, or **submission artifacts
  validated together**; these are report labels, not new values in the output CSV;
- whether root `output.csv` exists, its 518-row validation result, status distribution, selected run
  ID/checksum, producing code revision and matching usage ledger; say explicitly when no audited output exists;
- provider smoke results and which capabilities are live, offline-tested, stubbed or unavailable;
- up to five observed failure patterns with example case IDs, without inventing failures to fill the list;
- `[overnight]` decisions, explained regressions, remaining blockers and prioritized next actions;
- submission-checklist status, trace-export coverage and the last successfully published checkpoint.

Before stopping, finish reports/checklists as far as evidence allows, preserve the selected output,
verify available artifacts, export/verify the trace, commit `trace: overnight wrap-up`, and push.
Confirm the final working-tree/push status. If completion, export or publication is blocked, report
that accurately rather than claiming success.
