# Evaluation report — Ghost Data Still Exists

Built by `python code/evaluation/make_reports.py` from preserved artifacts (no model calls):
- selected final run `output_candidate_20261025T085130Z`, code revision `375604e2c3387748ee0c942e0c28e46433bcec9a`, output sha256 `09c8ecf6781e295799866b3e875c21f456de240f8d0b31f4b960a8f59ac786e3`;
- evaluation inputs `evaluation_inputs.json` captured 2026-10-25T10:31:54Z at code revision `0d7c07dd7504b2db865d59c59745f152a32e46af`
  (provider keys present: TYPESAFE_API_KEY, AZURE_OPENAI_API_KEY, GEMINI_API_KEY; default sample
  run model calls: {"attempts": 0, "cached_calls": 49, "calls": 0, "cost_usd": 0.0, "input_tokens": 0, "output_tokens": 0}).

**NOT a unified release:** the evaluation inputs and the selected final run come from different code revisions. Sample metrics below describe the evaluation-input revision, not the code that produced the selected output.

**Read this first.** The 32 public samples were inspected while designing the system, so every sample number is a
**regression-set** result, not untouched validation; the dev (20) / holdout (12) split was inspected too. Custom and
metamorphic cases are **custom validation** written around known risks. No untouched holdout exists, and nothing here
measures hidden-answer accuracy.

## 1. Sample regression set (default configuration)

| Run | Status acc | Account linkage | Step P / R / F1 | evidence_id acc | step_no acc | Sequence exact | Mean LCS |
|---|---|---|---|---|---|---|---|
| dev (20 cases) | 0.750 (15/20) | 7/20 | 0.990 / 0.824 / 0.900 | 0.903 | 0.738 | 0.250 (5/20) | 0.746 |
| holdout (12 cases) | 0.667 (8/12) | 5/12 | 0.966 / 0.824 / 0.889 | 0.893 | 0.732 | 0.333 (4/12) | 0.688 |
| all (32 cases) | 0.719 (23/32) | 12/32 | 0.981 / 0.824 / 0.896 | 0.899 | 0.736 | 0.281 (9/32) | 0.724 |

- **Case-level deletion-status accuracy:** 23/32 (0.719). 9 status misses; 9 of them are gold-COMPLETE cases whose account has no grounded link (ACCOUNT_UNGROUNDED keeps them INCOMPLETE by contract).
- **Account linkage (separate metric):** {'correct': 12, 'ungrounded': 20} over 32 cases; precision of grounded links 1.000.
- **Step-level accuracy** on keys (operation, system_id, resource_id): precision 0.981 (159/162 predicted steps), recall 0.824 (159/193 gold steps), F1 0.896.
- **Field-level accuracy on the 159 matched steps:** phase 1.000, state 1.000, evidence_id 0.899, step_no 0.736. 16 matched steps cite different evidence; 16 of them are in gold-COMPLETE cases predicted INCOMPLETE (future verification steps carry an empty evidence_id by contract).
- **Sequence accuracy:** 9/32 exact (0.281); mean normalized LCS 0.724. 9 of the 12 samples with a grounded account link have an exactly matching plan.
- Blocker / diagnostic flags (cases): {"ACCOUNT_UNGROUNDED": 20, "ACCOUNT_MULTI_GROUNDED": 1, "UNKNOWN_STATE": 2, "POLICY_UNDEFINED": 0, "EMPTY_OBLIGATIONS": 3, "REQUIRED_RECORD_MISSING": 0, "CONDITION_DEFAULTED": 19, "ACTIVITY_CITATION": 0, "IDENTITY_SNAPSHOT_AFTER_CUTOFF": 0}.

## 2. Discovery coverage

End-to-end discovery on the samples (`code/tools/discovery_report.py`; gold is used only to score):
resource recall 77/111 (69.4%; spec 0010 target ≥ 85%: **unmet**), current accounts 12/32, other resources 65/79, 3 extra grounded resources, linkage precision 12/12.
Miss causes (participant-visible evidence at each audit_at): {"eligible_records_without_ownership": 12, "no_participant_evidence": 3, "post_cutoff_evidence_only": 5, "workflow_claims_only": 14}.
See `code/docs/DISCOVERY_GAP_REVIEW.md`.

## 3. Custom validation cases (participant-created, not a holdout)

8 cases (9 requests) under `code/evaluation/cases/`, each an overlay on a temporary copy of
`dataset/` with an expected output written from the rules and a rationale README.
9/9 requests fully pass.

| case | request | expected | got | status | steps | flags | validator | flags seen |
|---|---|---|---|---|---|---|---|---|
| expired_retention | case_9006 | INCOMPLETE | INCOMPLETE | pass | pass | pass | pass | POLICY_UNDEFINED |
| historical_email_decoy | case_9001 | INCOMPLETE | INCOMPLETE | pass | pass | pass | pass |  |
| non_deletion_multilingual | case_9003 | NOT_APPLICABLE | NOT_APPLICABLE | pass | pass | pass | pass |  |
| post_audit_evidence_ignored | case_9002 | COMPLETE | COMPLETE | pass | pass | pass | pass |  |
| repeated_request | case_9071 | INCOMPLETE | INCOMPLETE | pass | pass | pass | pass |  |
| repeated_request | case_9072 | COMPLETE | COMPLETE | pass | pass | pass | pass |  |
| retained_backup_blocked | case_9005 | COMPLETE | COMPLETE | pass | pass | pass | pass | CONDITION_DEFAULTED |
| tombstone_active_sync | case_9004 | INCOMPLETE | INCOMPLETE | pass | pass | pass | pass |  |
| ungrounded_account | case_9008 | INCOMPLETE | INCOMPLETE | pass | pass | pass | pass | ACCOUNT_UNGROUNDED CONDITION_DEFAULTED |

## 4. Recorded test runs

`code/tests/test_metamorphic.py`: a post-cutoff audit row per subject, shuffled CSV rows and an unrelated user's identity
and evidence leave outputs unchanged; moving `evidence_54` after every audit_at changes only the cases that used it.

| Suite | Command | Exit code | Result |
|---|---|---|---|
| full_suite | `python -m pytest code/tests -q` | 0 | 144 passed, 2 skipped |
| metamorphic | `python -m pytest code/tests/test_metamorphic.py -q` | 0 | 4 passed |

## 5. Ablations (samples, all 32)

| Run | Status acc | Account linkage | Step P / R / F1 | evidence_id acc | step_no acc | Sequence exact | Mean LCS |
|---|---|---|---|---|---|---|---|
| deterministic-only: no model calls (`--offline --no-cache`) | 0.656 (21/32) | 10/32 | 0.993 / 0.751 / 0.855 | 0.924 | 0.738 | 0.219 (7/32) | 0.634 |
| no historical identifiers (`--ablate no-history`) | 0.688 (22/32) | 12/32 | 0.981 / 0.808 / 0.886 | 0.885 | 0.718 | 0.250 (8/32) | 0.705 |
| trust activity claims (`--ablate trust-claims`) | 0.719 (23/32) | 12/32 | 0.981 / 0.824 / 0.896 | 0.899 | 0.736 | 0.281 (9/32) | 0.724 |
| ranked guessed accounts, INCOMPLETE only (`--ungrounded-account-steps ranked`) | 0.719 (23/32) | 12/32 grounded; 8 right / 12 wrong guesses | 0.918 / 0.865 / 0.891 | 0.892 | 0.880 | 0.375 (12/32) | 0.812 |

The deterministic-only run uses the keyword intent check and has no PNG facts or category fallback. The ranked-account
ablation plans the top-ranked guessed account in INCOMPLETE output only and is never the submitted configuration.
Trust-claims injects SUCCESS operational claims as if they were observations. Full-dataset ablations are not measured.

## 6. Selected final run diagnostics (518 requests)

- Status distribution: {'COMPLETE': 47, 'INCOMPLETE': 461, 'NOT_APPLICABLE': 10}.
- Account link: {'grounded': 166, 'ungrounded': 342} (non-deletion requests have no link).
- Flags: {'ACCOUNT_UNGROUNDED': 342, 'CONDITION_DEFAULTED': 338, 'EMPTY_OBLIGATIONS': 1, 'UNKNOWN_STATE': 2}.

## 7. Failures found and improvements made

Recorded at the commit that made each change (sample regression set; "oracle-assisted" = the check was
given the gold resource ids and operations, so it measures a component, not end-to-end discovery):

| Spec / commit | Failure found | Change | Measured effect (as recorded then) |
|---|---|---|---|
| 0007 `2cb0e29` | Six log formats; lookup key and resource id sit on different lines of one trace | one line parser per format, records = trace_id groups | sample identifier reach 76/111 |
| 0009 `04c26e4` | PNG screens were unread; decoy company emails visible on screens | Gemini extraction (cached) + regex/identity-universe revalidation | 23 PNG records; none of the 8 unreachable resources appears in a PNG |
| 0010 `f63f611` | `cache_lookup result=miss` inside a trace read as "record absent"; completed reads not counted as presence | infrastructure lines excluded; completed reads count as presence | oracle-assisted state agreement 99 → 104/111, proofs 71 → 75/75 |
| 0012 `14df3a9` | generic snapshots claimed coverage of collections absent from the whole file | coverage only for collections present in that snapshot | no score change; removes an unsupported absence proof |
| 0013 `0623153` | negated requests contain deletion words | keyword check is a cross-check only; disagreements adjudicated by Azure | 10/10 non-deletion requests and 32/32 sample deletions classified correctly |
| 0017 `4f2a05a` | a newer primary-only read or clean record hid an uncleared replica; a newer package of an older read overwrote newer state | state per storage copy, violation wins; observation-time ordering; bundle omissions scoped to their subjects | sample outputs unchanged; full-dataset 3 obligations changed (0 COMPLETE → INCOMPLETE); oracle-assisted state 103/111 |
| 0018 `b0c7f27` | absence satisfied REDACT / ANONYMIZE / retained-backup obligations | separate preservation predicate, REQUIRED_RECORD_MISSING blocker | sample outputs unchanged; 0 full-dataset changes |
| 0019 `52a1854` | 34 sample resources ungrounded | investigation only: no defensible pre-cutoff link exists (`DISCOVERY_GAP_REVIEW.md`) | recall unchanged; the 0010 ≥85% target stays unmet |
| 0020 | reports claimed every grounded sample had an exact plan and depended on ignored `runs/` files | claims derived from per-case scores; hashed evaluation inputs; explicit input errors | this report |
