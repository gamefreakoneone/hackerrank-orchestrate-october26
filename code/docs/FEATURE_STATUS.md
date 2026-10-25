# FEATURE_STATUS — spec ledger

Single source of truth for what is done and what is next. Work specs in numeric order; never start a
spec whose dependencies are not `Completed`.

| Spec | Name | Status | Depends on | Deliverable |
|---|---|---|---|---|
| 0001 | [scaffold-env-logging](specs/0001-scaffold-env-logging/) | Completed | none | Runnable skeleton: dependencies pinned, env template, README skeleton, a `main.py` that writes a valid all-NOT_APPLICABLE `output.csv`, and a provider smoke test. |
| 0002 | [dataset-recon](specs/0002-dataset-recon/) | Completed | none | Understand the dataset and the gold format before designing; answer the HANDOFF §3 open questions. |
| 0003 | [data-contracts-loaders](specs/0003-data-contracts-loaders/) | Completed | 0001 | Typed, timezone-aware loaders for every CSV and the Key Contract models. |
| 0004 | [serializer-validator](specs/0004-serializer-validator/) | Completed | 0003 | Deterministic output writer and a hard validator for every output rule. |
| 0005 | [scorer-and-split](specs/0005-scorer-and-split/) | Completed | 0004 | Grader-replica scorer, frozen dev/holdout split, baseline numbers. |
| 0006 | [identity-resolution](specs/0006-identity-resolution/) | Completed | 0003 | Resolve the subject and every identifier valid at or before audit_at. |
| 0007 | [evidence-parsers](specs/0007-evidence-parsers/) | Completed | 0003, 0006 | Parse every non-image evidence file once into Observations with an inverted index. |
| 0008 | [llm-provider-layer](specs/0008-llm-provider-layer/) | Completed | 0001 | Single structured-call layer for Jev, Azure (Strands) and Gemini (Strands) with cache and usage ledger. |
| 0009 | [vision-extraction](specs/0009-vision-extraction/) | Completed | 0007, 0008 | Turn the 11 PNG screenshots into Observations. |
| 0010 | [discovery-and-state](specs/0010-discovery-and-state/) | Completed | 0006, 0007 (0009 optional) | Find every resource relevant to the subject and its state at audit_at. |
| 0011 | [policy-obligations](specs/0011-policy-obligations/) | Completed | 0010 | Turn discovered resources + rules into obligations with satisfied/unsatisfied state. |
| 0012 | [planner-and-evidence](specs/0012-planner-and-evidence/) | Completed | 0004, 0011 | Status decision, full step plan, deterministic evidence citation; end-to-end on samples. |
| 0013 | [intent-gate](specs/0013-intent-gate/) | Completed | 0008, 0012 | Decide whether request_text authorizes deletion (multilingual). |
| 0014 | [custom-eval-and-metamorphic](specs/0014-custom-eval-and-metamorphic/) | Completed | 0012, 0013 | Team-created evaluation cases and metamorphic tests (problem statement requires ≥3 custom cases). |
| 0015 | [full-run-ablations-reports](specs/0015-full-run-ablations-reports/) | Completed | 0014 | Final cold-cache full run, ablations, and the two required evaluation reports. |
| 0016 | [packaging-and-interview](specs/0016-packaging-and-interview/) | Completed | 0015 | Submission artifacts and interview preparation. |
| 0017 | [replica-state-and-proof](specs/0017-replica-state-and-proof/) | Completed | 0010, 0012, 0016 | Per-copy state and treatment evidence; prevent a primary-only result from clearing another replica. |
| 0018 | [required-record-preservation](specs/0018-required-record-preservation/) | Completed | 0017 | Enforce record preservation separately from redaction/anonymization/restore blocking. |
| 0019 | [grounded-discovery-coverage](specs/0019-grounded-discovery-coverage/) | Completed (investigation only) | 0018 | Evidence-backed discovery improvements or a measured, documented no-improvement outcome. |
| 0020 | [reproducible-evaluation-reports](specs/0020-reproducible-evaluation-reports/) | Completed | 0019 | Rebuild truthful reports from preserved artifacts, with correct validation commands and explicit errors. |
| 0021 | [validated-final-run-packaging](specs/0021-validated-final-run-packaging/) | Completed | 0020 | Candidate-first validated output publication and a consistent final run/report/package bundle. |

## Current correction pass

The overnight implementation is the historical baseline at `2a722566e1367f409a5b3789ce61c1c19c566cfc`,
originally pushed on `claude/nifty-tesla-4ig5f5` and fast-forwarded into `claude/eager-cray-7fhtkf` for this pass.
Follow `CORRECTIVE_HANDOFF.md` and `reviews/0001-implementation-review.md`. Work branch (cloud session's designated
push branch): `claude/specs-0017-0021-5s3kpe`, started from `origin/claude/eager-cray-7fhtkf` @ `bf79d4a`.
**0017–0021 Completed.** Selected output: run `0021_candidate_20261025T104010Z`, producing code `b90914b`, sha256 `81b31784…0ecb`.

The original 0001–0016 statuses record the overnight milestones, not a claim that all current correctness or
acceptance gaps are closed. In particular, 0010 reported Completed with recall **77/111 versus the ≥85% target**;
that target remains an explicitly unmet historical acceptance criterion.
Preserve historical measurements; report new measurements with their own code revision/configuration. Do not
mark a corrective spec Completed when a mandatory check fails or turn a coverage limitation into a guessed link.

### Corrective publication record

Each spec commit is pushed and verified on the remote before the next spec starts; SHAs are filled in by the next
commit (a commit cannot contain its own SHA).

| Spec | Commit | Remote branch | Verified |
|---|---|---|---|
| 0017 | `4f2a05a` | `claude/specs-0017-0021-5s3kpe` | yes — `git fetch` showed remote = local `4f2a05a3a930` |
| 0018 | `b0c7f27` | `claude/specs-0017-0021-5s3kpe` | yes — `git fetch` showed remote = local `b0c7f275cfe8` |
| 0019 | `52a1854` | `claude/specs-0017-0021-5s3kpe` | yes — `git fetch` showed remote = local `52a1854e805b` |
| 0020 checkpoint | `0d7c07d` (code freeze recorded in the evaluation bundle) | `claude/specs-0017-0021-5s3kpe` | yes — remote = local `0d7c07dd7504` |
| 0020 | `6907176` | `claude/specs-0017-0021-5s3kpe` | yes — remote = local `69071766462e` |
| 0021 checkpoint | `b90914b` (producing code of the final run) | `claude/specs-0017-0021-5s3kpe` | yes — remote = local `b90914b52411` |
| 0021 bundle | `67bb114` (evaluation inputs at `b90914b`; artifacts only) | `claude/specs-0017-0021-5s3kpe` | yes — remote `67bb114a4aa0` |
| 0021 | `spec 0021: validate final run and submission bundle` | `claude/specs-0017-0021-5s3kpe` | see the log / final report |

## Planning history

- Phase 0 (`66e8559`): design, spec plan, data-derived decisions.
- Codex review `code/docs/reviews/0000b-codex-phase0-review.md` (`283fc2f`) → Phase 0b planning corrections:
  cutoff-safe exact baselines, subject-level account linking (no one-to-one assignment), `SnapshotCoverage`,
  completion blockers, activity/audit citation fallback, tri-state policy conditions, PNG checks for the 8
  unreachable resources, samples treated as a regression set, scorer tables in 0005 and 0008.
- Second review of `d440ced` → Phase 0c: asserted absence rule (0b claim was 3/4), strict identity cutoff,
  grounded account links required for COMPLETE (`ACCOUNT_UNGROUNDED`), state-check vs operational activity,
  `[]` validator rule, FALSE conditions ⇒ `POLICY_UNDEFINED` (no inferred inverse), custom validation ≠ holdout.
- Third review of `290b4fb` → Phase 0d: no stale-snapshot fallback, historical grounded accounts kept, post-cutoff
  identity snapshots excluded, activity observations in the contract. **Phase 0 closed; next: spec 0001** (new
  session).

## Status definitions

- **Not started** — no code for this spec exists.
- **In progress** — work begun on the branch; `status.md` lists what remains.
- **Blocked** — cannot proceed; `status.md` names the blocker and what is needed.
- **Completed** — every task checked, validation commands run, evidence (test counts, scorer numbers)
  pasted into `status.md`, committed as `spec NNNN: <summary>`. Push and verify that commit before proceeding;
  record a publication blocker if it is not yet on the remote. Historical exceptions are called out above.

## Update rule

When a spec's status changes, update this table, the spec's `status.md`, and its `tasks.md` checkboxes in
the **same commit**. From spec 0005 onward, `status.md` must carry the dev-split scorer snapshot
(status accuracy, step F1, sequence exact-match) before and after the change.
