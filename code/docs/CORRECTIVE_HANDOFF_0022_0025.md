# Claude implementation handoff — specs 0022–0025

## Branch and starting point

- **Repository:** `gamefreakoneone/hackerrank-orchestrate-october26`
- **Work and push branch:** `claude/specs-0017-0021-5s3kpe`
- **Audited implementation:** `88a357ea152601aeca3ce5cc98e0fd764597b1c6`
- **Next work:** 0022, then 0023, 0024 and 0025, one spec/commit at a time.
- **Current state:** these four specs are Not started. This handoff adds documentation, not runtime corrections.

The branch name retains the previous pass's numbers deliberately: continue its history with the new specs.
Do not implement against the older `claude/eager-cray-7fhtkf` / `bf79d4a` checkout or restart Phase 0.
Pull the latest documentation commit on this branch before editing. The audited SHA is a provenance anchor,
not an instruction to reset the branch backwards.

## Copy-paste prompt for Claude Code

```text
Work on gamefreakoneone/hackerrank-orchestrate-october26,
branch claude/specs-0017-0021-5s3kpe. Only one agent may write this branch.

Read @AGENTS.md and @CLAUDE.md first. Inspect git status and preserve unrelated work.
If necessary, fetch origin and switch to claude/specs-0017-0021-5s3kpe
(create a tracking branch from origin/claude/specs-0017-0021-5s3kpe if absent).
Then run:
  git pull --rebase origin claude/specs-0017-0021-5s3kpe
  git rev-parse HEAD
  git merge-base --is-ancestor 88a357ea152601aeca3ce5cc98e0fd764597b1c6 HEAD
Do not reset, force-push, or silently work on eager-cray/main. If this branch cannot
be checked out or pushed, report the restriction before choosing another branch.

Append SESSION START and one entry per user turn to root log.txt. Use your actual
harness tool= and exact runtime model=, verified from runtime metadata. Follow the
append-only, verbatim-prompt and secret-redaction requirements in AGENTS.md.
No challenge deadline is configured; do not invent one.

Read in full:
  @problem_statement.md
  @code/docs/FEATURE_STATUS.md
  @code/docs/TECHNICAL_DESIGN.md
  @code/docs/reviews/0002-corrective-pass-review.md
  @code/docs/CORRECTIVE_HANDOFF_0022_0025.md
  @code/docs/MORNING_REPORT.md
  @agent_trace_instructions.md
For historical context also read:
  @code/docs/reviews/0001-implementation-review.md
  @code/docs/CORRECTIVE_HANDOFF.md
  @code/docs/DISCOVERY_GAP_REVIEW.md

Implement the next Not started spec among 0022–0025, in numeric order. Read its
requirements.md, design.md, tasks.md and status.md before editing; read the owning
0017/0018/0020/0021 contract files when a new spec references them. Dependencies
must be completed and remotely published before starting the next spec.

Spec folders:
  code/docs/specs/0022-observation-time-cutoffs/
  code/docs/specs/0023-unknown-copy-treatment/
  code/docs/specs/0024-final-artifact-hash-verification/
  code/docs/specs/0025-selected-output-configuration-guards/

Verify the review's claims against code and participant data. B1 affects saved
case_135 and case_383; the other findings are reproduced code defects whose saved
output impact is not established. Regression IDs are allowed in tests/review
tooling, never as runtime prediction shortcuts. The review is a targeted audit,
not a completed sign-off on every original audit question.

Use only dataset/ for inference; sample_output.csv is an evaluation oracle only.
Keep grounded links, historical identities, strict temporal cutoffs, per-copy
state, required record preservation, allowed operations and deterministic order.
Models return typed facts/enum choices; code owns status, steps and citations.
Apply YAGNI, DRY after real duplication, explicit failures and semantic naming.
Remove replaced paths only after their replacements are verified.

Budget and artifacts:
  - RUN_LIVE must be unset for tests.
  - Follow each tasks.md offline/no-cache sample commands and record that mode.
  - Missing caches are expected. A cache miss is not permission to call a provider.
  - Any live provider run requires separate user permission. Do not run the full
    518-case live pipeline under this handoff alone.
  - Read evidence summaries, not whole evidence files or system_activity.csv.
  - Keep root output.csv, code/evaluation/final_run/ and
    code/evaluation/corrective_run/ as historical artifacts during the fixes.
    Write comparisons/candidates under runs/corrective/ or an isolated temporary
    fixture. Never alter saved predictions to satisfy tests.
  - The preserved live sample score is not an offline/no-cache baseline. Record
    before/after dev metrics under the same actual configuration; label anything
    not run as not measured. Do not fabricate a full-run improvement from a
    component counterfactual.

After each spec:
  1. Run its required checks; retain correctness fixes even if sample metrics fall,
     explaining why. A failed mandatory check means Blocked, not Completed.
  2. Update status.md, tasks.md, FEATURE_STATUS.md and MORNING_REPORT.md together;
     update the owning Key Contracts and code/README.md where behavior changes.
  3. Append the log. Export and verify YOUR ACTUAL harness trace immediately before
     committing. For Claude Code, use actual session metadata with save_trace.sh
     per CLAUDE.md, and verify the intended JSONL was refreshed and parses: its
     exit code alone is not proof. Redact secrets and retain useful tool content.
  4. Commit that spec, push to claude/specs-0017-0021-5s3kpe, and verify the remote
     contains the commit before starting the next spec. Never force-push. A failed
     push is a publication blocker; preserve the local commit and report it.

After 0025, distinguish corrected-code completion from release regeneration.
The preserved output has a confirmed temporal defect and cannot be relabelled as
produced by the new code. Ask for permission before refreshing a live evaluation
bundle/full candidate. If authorized, freeze/push the producing code, preserve
matching evaluation inputs and usage, validate a separate candidate, finalize the
matching bundle, and rebuild/verify the package. Otherwise report release
regeneration pending, with the existing output left intact. Do not submit anything.

Finish with actual pushed SHAs/branch, checks and configurations, before/after
metrics, unresolved questions, artifact readiness and the next action.
```

## Ownership map

| Spec | Confirmed finding | Primary implementation area |
|---|---|---|
| 0022 | B1: future observations backdated into current state | evidence eligibility/parsers, timeline and temporal consumers |
| 0023 | M1: unknown treatment copy dropped | obligations, per-copy diagnostics and completion blockers |
| 0024 | M2: final diagnostics/ledger hashes unchecked by report loader | make_reports and integrity fixtures/callers |
| 0025 | M3: non-release runs can target selected output | main CLI guard, finalizer mode checks and publication tests |

## Baseline and boundaries

The targeted review independently exercised the pinned validator/scorer/report functions in memory and checked
artifact hashes. It did **not** rerun pytest or the actual clean-room CLI workflow. Preserve that distinction when
starting implementation. See the review's reproduction table and outstanding-audit list.

The old discovery target remains unmet: 77/111 versus at least 85% (95/111). No grounded discovery improvement was
established by this review, so these specs do not authorize guessed links. Raw-source discovery checks, remaining
historical narrative claims and finalizer interruption/provenance caveats remain investigation questions, not new
confirmed defect specs.

`code/evaluation/final_run/manifest.json` identifies producing revision `b90914b524111fb284f8a8a8bcf3c5b7ecb5835a`.
The selected output hash is `81b317844674c62981d43b3c6eb575fc30520737d5e32078de3ea9a86e9e0ecb`.
Do not replace either with the later documentation/spec commit's revision.
