# Overnight kickoff prompt

Finish and push the previous writer's session before starting a new cloud session on
`claude/eager-cray-7fhtkf`. Ensure this prompt and `OVERNIGHT_RUN.md` are committed on that branch.
Only one agent should write the branch during the run. Configure any time/spend limits and provider
credentials in the new session's environment; a previous session's `.env` is not transferred by Git.

Paste the following into the new implementation-capable session:

```text
Inspect git status first. Do not discard unrelated work. For a clean checkout, run:
git fetch origin
git checkout claude/eager-cray-7fhtkf
git pull --ff-only origin claude/eager-cray-7fhtkf

Read AGENTS.md, CLAUDE.md, code/docs/TECHNICAL_DESIGN.md,
code/docs/FEATURE_STATUS.md, and code/docs/OVERNIGHT_RUN.md.
Follow the corrected overnight brief end to end, unattended, starting at section 1
and the next unfinished spec. Phase 0 is closed; implement rather than redo planning.

Follow numeric spec order and prerequisite checks. Resolve routine implementation
choices within the contracts and document them. If blocked, record the reason and
continue only with independent eligible work. Do not ask routine clarification
questions, weaken evidence rules, or mark failed prerequisites Completed.

Do not invent evidence, identity links, passing tests, provider availability,
deadlines or completion. Use exact eligible identifiers; abbreviated excerpts and
unique prefixes are not grounding. Keep ranked accounts in diagnostics except for
the explicitly labelled INCOMPLETE-only ablation.

Use sample runs during development. Keep scaffold, ablation and final outputs
distinct. A schema-valid 518-row baseline is not a submission-ready audit.
Preserve the selected final output and its matching code revision, diagnostics
and usage ledger. Retain explained correctness-driven metric regressions.

After each spec, record validation and measured metrics, update the morning report
and submission checklist, export and verify the actual session trace, then commit
and push. Use real runtime tool/model identifiers and session metadata. Follow the
brief's bounded retry, resource-limit and checkpoint rules.

Finish with section 6's wrap-up procedure. Package artifacts and report their
readiness and remaining blockers. Do not submit automatically.
```

Morning handover: start with `code/docs/MORNING_REPORT.md` and
`code/docs/SUBMISSION_CHECKLIST.md`, then the selected run's reports and diagnostics.
Confirm artifact consistency before further fixes or any separately authorized submission.
