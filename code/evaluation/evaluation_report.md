# Evaluation report — Ghost Data Still Exists

Produced by `python code/evaluation/make_reports.py` from the artifacts of the selected final run
(`output_candidate_20261025T085130Z`, code revision `375604e2c3387748ee0c942e0c28e46433bcec9a`, output sha256 `09c8ecf6781e295799866b3e875c21f456de240f8d0b31f4b960a8f59ac786e3`).

**Read this first.** The 32 public samples were inspected while designing the system (Phase 0), so every sample number
below is a **regression-set** result, not untouched validation; the frozen dev (20) / holdout (12) split is reported
separately but both parts were inspected. The custom and metamorphic cases were written around known risks and are
**custom validation**, not a holdout. No untouched holdout exists, and nothing here measures hidden-answer accuracy.

## 1. Sample regression set (default configuration)

| Run | Status acc | Account linkage | Step P / R / F1 | evidence_id acc | step_no acc | Sequence exact | Mean LCS |
|---|---|---|---|---|---|---|---|
| dev (20 cases) | 0.750 (15/20) | 7/20 | 1.000 / 0.824 / 0.904 | 0.903 | 0.728 | 0.250 (5/20) | 0.746 |
| holdout (12 cases) | 0.667 (8/12) | 5/12 | 0.966 / 0.824 / 0.889 | 0.893 | 0.732 | 0.333 (4/12) | 0.688 |
| all (32 cases) | 0.719 (23/32) | 12/32 | 0.988 / 0.824 / 0.898 | 0.899 | 0.730 | 0.281 (9/32) | 0.724 |

- **Case-level deletion-status accuracy:** 0.719 on all 32 samples. All misses are gold-COMPLETE
  cases whose account has no grounded link (ACCOUNT_UNGROUNDED keeps them INCOMPLETE by design); 23/32 is exactly the
  conditional upper bound recorded before implementation.
- **Account-linkage accuracy (separate metric):** {'correct': 12, 'ungrounded': 20} — precision on grounded links
  1.000; the remaining cases have no grounded link in the eligible evidence.
- **Step-level accuracy** on keys (operation, system_id, resource_id): precision 0.988, recall
  0.824, F1 0.898 (159 matched of
  161 predicted / 193 gold steps).
- **Field-level accuracy on matched steps:** phase 1.000, state 1.000, evidence_id
  0.899, step_no 0.730. evidence_id differences are verification steps of
  gold-COMPLETE cases we keep INCOMPLETE (empty evidence_id by contract); step_no shifts follow from missing steps.
- **Sequence accuracy:** exact match 0.281; mean normalized LCS 0.724.
  Every sample whose account link is grounded has an exactly matching plan.
- Blocker / diagnostic flags on samples: {"ACCOUNT_UNGROUNDED": 20, "ACCOUNT_MULTI_GROUNDED": 1, "UNKNOWN_STATE": 0, "POLICY_UNDEFINED": 0, "EMPTY_OBLIGATIONS": 3, "CONDITION_DEFAULTED": 19, "ACTIVITY_CITATION": 0, "IDENTITY_SNAPSHOT_AFTER_CUTOFF": 0}.

## 2. Custom validation cases (participant-created, not a holdout)

Eight cases (nine requests) under `code/evaluation/cases/`, each with an overlay on a temporary copy of `dataset/`, an
expected output written from the rules and committed before the first run (`d33daa7`), and a rationale README.

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

9/9 requests fully pass


## 3. Metamorphic tests

`code/tests/test_metamorphic.py` (current result: `4 passed`): a post-cutoff audit row per subject leaves every output
unchanged; shuffling the rows of every CSV leaves outputs unchanged; adding an unrelated user's identity and evidence
leaves outputs unchanged; moving `evidence_54` after every audit_at removes it from all citations and changes only the
cases that used it as proof, link or snapshot-omission candidate.

## 4. Ablations (samples, all 32)

| Run | Status acc | Account linkage | Step P / R / F1 | evidence_id acc | step_no acc | Sequence exact | Mean LCS |
|---|---|---|---|---|---|---|---|
| default (submitted configuration) | 0.719 (23/32) | 12/32 | 0.988 / 0.824 / 0.898 | 0.899 | 0.730 | 0.281 (9/32) | 0.724 |
| deterministic-only: no model calls (`--offline --no-cache`) | 0.656 (21/32) | 10/32 | 0.993 / 0.751 / 0.855 | 0.924 | 0.738 | 0.219 (7/32) | 0.634 |
| no historical identifiers (`--ablate no-history`) | 0.688 (22/32) | 12/32 | 0.987 / 0.808 / 0.889 | 0.885 | 0.712 | 0.250 (8/32) | 0.705 |
| trust activity claims (`--ablate trust-claims`) | 0.719 (23/32) | 12/32 | 0.988 / 0.824 / 0.898 | 0.899 | 0.730 | 0.281 (9/32) | 0.724 |
| ranked guessed accounts, INCOMPLETE only (`--ungrounded-account-steps ranked`) | 0.719 (23/32) | 12/32 grounded; 8 right / 12 wrong guesses | 0.923 / 0.865 / 0.893 | 0.892 | 0.886 | 0.406 (13/32) | 0.818 |

Notes: the deterministic-only run uses the keyword intent check (marked provisional) and has no PNG facts or category
fallback. The ranked-account ablation plans the top-ranked guessed account in INCOMPLETE output only (it can never make a
case COMPLETE); it is never the submitted configuration. Trust-claims injects SUCCESS operational claims as if they were
observations; on these samples evidence captured after the claims dominates, so only proofs change.

Full-dataset status distribution per configuration (518 requests, no answers available):

| Configuration | COMPLETE | INCOMPLETE | NOT_APPLICABLE |
|---|---|---|---|
| default (submitted output) | 47 | 461 | 10 |
| deterministic-only: no model calls (`--offline --no-cache`) | 48 | 463 | 7 |
| no historical identifiers (`--ablate no-history`) | 38 | 470 | 10 |
| trust activity claims (`--ablate trust-claims`) | 47 | 461 | 10 |
| ranked guessed accounts, INCOMPLETE only (`--ungrounded-account-steps ranked`) | 47 | 461 | 10 |

## 5. Final run diagnostics (518 requests)

- Status distribution: {'INCOMPLETE': 461, 'COMPLETE': 47, 'NOT_APPLICABLE': 10}.
- Account link: {'ungrounded': 342, 'grounded': 166} (non-deletion requests have no link).
- Flags: {'ACCOUNT_UNGROUNDED': 342, 'CONDITION_DEFAULTED': 338, 'EMPTY_OBLIGATIONS': 1, 'UNKNOWN_STATE': 2}.

## 6. Failures found and improvements made

| Spec / commit | Failure found | Change | Measured effect |
|---|---|---|---|
| 0007 `2cb0e29` | Six log formats; lookup key and resource id sit on different lines of one trace | one line parser per format, records = trace_id groups | sample identifier reach 76/111 (Phase-0b reference 77/111) |
| 0009 `04c26e4` | PNG screens were unread; decoy company emails visible on screens | Gemini extraction (cached) + regex/identity-universe revalidation | 23 PNG records; none of the 8 previously unreachable resources appears in a PNG (reach stays 103/111) |
| 0010 `f63f611` | `cache_lookup result=miss` merged into a trace was read as "record absent" (case_15 audit_record_1596) | infrastructure lines excluded from trace records | state agreement 99 → 104/111 (with the next two fixes) |
| 0010 `f63f611` | readback `*_read_completed` events not recognised as presence (case_03, case_18) | completed reads count as presence | gold-cited proofs 71 → 75/75 |
| 0010 `f63f611` | a later primary-only inventory overrode a replica that still held the account (case_05 replica drift) | omission must cover the replica where the record was last seen | case_05 PRESENT with evidence_54, as gold |
| 0012 `14df3a9` | generic snapshots claimed coverage of collections absent from the whole file (tombstone_17 "absent") | coverage only for collections present in that snapshot | no score change; removes an unsupported absence proof |
| 0013 `0623153` | negated requests ("not asking for deletion") contain deletion words | keyword check is a cross-check only; disagreements adjudicated by Azure | 10/10 non-deletion requests and 32/32 sample deletions classified correctly |
| 0010–0012 (kept) | 20/32 samples (342/508 deletion requests in the final run) have no grounded subject→account link | **not changed**: ranked guesses stay in diagnostics (contract) | status capped at the conditional bound 23/32; see the ranked-account ablation |

