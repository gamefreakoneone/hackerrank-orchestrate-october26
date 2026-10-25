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
| 0010 | [discovery-and-state](specs/0010-discovery-and-state/) | Not started | 0006, 0007 (0009 optional) | Find every resource relevant to the subject and its state at audit_at. |
| 0011 | [policy-obligations](specs/0011-policy-obligations/) | Not started | 0010 | Turn discovered resources + rules into obligations with satisfied/unsatisfied state. |
| 0012 | [planner-and-evidence](specs/0012-planner-and-evidence/) | Not started | 0004, 0011 | Status decision, full step plan, deterministic evidence citation; end-to-end on samples. |
| 0013 | [intent-gate](specs/0013-intent-gate/) | Not started | 0008, 0012 | Decide whether request_text authorizes deletion (multilingual). |
| 0014 | [custom-eval-and-metamorphic](specs/0014-custom-eval-and-metamorphic/) | Not started | 0012, 0013 | Team-created evaluation cases and metamorphic tests (problem statement requires ≥3 custom cases). |
| 0015 | [full-run-ablations-reports](specs/0015-full-run-ablations-reports/) | Not started | 0014 | Final cold-cache full run, ablations, and the two required evaluation reports. |
| 0016 | [packaging-and-interview](specs/0016-packaging-and-interview/) | Not started | 0015 | Submission artifacts and interview preparation. |

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
  pasted into `status.md`, committed as `spec NNNN: <summary>`.

## Update rule

When a spec's status changes, update this table, the spec's `status.md`, and its `tasks.md` checkboxes in
the **same commit**. From spec 0005 onward, `status.md` must carry the dev-split scorer snapshot
(status accuracy, step F1, sequence exact-match) before and after the change.
