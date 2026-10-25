# Spec 0014 — custom-eval-and-metamorphic: status

**Status:** Completed (2026-10-25, overnight run)

These are **custom and metamorphic validation** cases designed around known risks — not a holdout.

## Evidence

```text
Expected outputs were written from the rules and committed before any pipeline run: d33daa7
$ python code/evaluation/run_custom.py                 # runs/custom/results.md
9/9 requests fully pass (status, exact steps, expected flags present/absent, validator)
$ python -m pytest code/tests/test_metamorphic.py -q
4 passed
$ python -m pytest code/tests -q
108 passed, 2 skipped
$ python code/evaluation/run_eval.py --split dev
status 0.750, F1 0.904, sequence exact 0.250 (unchanged)
```

| case | request(s) | risk covered | expected | result |
|---|---|---|---|---|
| historical_email_decoy | case_9001 | historical request email; decoy names ('Elin Strand' with another email, 'Elin Strandberg') | INCOMPLETE: search record remains, account absent | pass |
| post_audit_evidence_ignored | case_9002 | snapshot captured after audit_at with an earlier-dated row | COMPLETE citing only the eligible readback | pass |
| non_deletion_multilingual | case_9003 | German access request that keeps the account | NOT_APPLICABLE, `[]` | pass |
| tombstone_active_sync | case_9004 | tombstone still holding name/email + enabled connector | INCOMPLETE: expose + active flow; disable before redact | pass |
| retained_backup_blocked | case_9005 | retained backup with restore blocked + audit record in retention | COMPLETE, 3 cited verifications; CONDITION_DEFAULTED | pass |
| expired_retention | case_9006 | retention_until before audit_at (condition FALSE) | INCOMPLETE, POLICY_UNDEFINED, no inferred DELETE, no step for the record | pass |
| repeated_request | case_9071, case_9072 | same subject, two cutoffs | INCOMPLETE then COMPLETE, each with its own evidence | pass |
| ungrounded_account | case_9008 | only an identifier-free DELETE_RECORD claim names the account | INCOMPLETE, ACCOUNT_UNGROUNDED, no account step | pass |

**Cases that drove fixes:** none — all passed on the first run, so no code was changed because of them.

Metamorphic tests (`code/tests/test_metamorphic.py`, samples, assess+plan without models):
1. a post-cutoff audit row (email change) for every sample subject → outputs unchanged;
2. shuffled row order in every CSV (identities, audit, activity, manifest, rules, requests) → unchanged;
3. an unrelated user with an identity row and a readback log → unchanged;
4. evidence_54 moved after every audit_at → it is never cited, and only cases that used it change (as proof, link, or
   eligible snapshot-omission candidate): case_05 (its only grounding) and case_24. case_24 shows a property of the
   §5 Q2 absence rule: with evidence_54 present the rule prefers that older replica-covering snapshot (which predates
   the account's 09-15 presence, so the account stays PRESENT, matching gold); without it the newer evidence_51 bundle
   omission becomes the candidate and the account turns ABSENT.

## Scorer snapshot (dev)

| | Status acc | Account linkage | Step F1 | Seq exact |
|---|---|---|---|---|
| before (0013) | 0.750 | 7/20 | 0.904 | 0.250 |
| after | 0.750 | 7/20 | 0.904 | 0.250 |

## Notes

- `code/evaluation/cases/<name>/{request.csv, overlay/, expected.csv, expected_flags.json, README.md}`; overlay CSVs
  are appended to a temporary copy of dataset/ (`runs/custom/tmp_<name>/`), other files are added; `request.csv`
  replaces `deletion_requests.csv`. dataset/ is never edited. Fictional people on the reserved `example.net` domain.
- `main.py --data-root DIR` added; README updated.
