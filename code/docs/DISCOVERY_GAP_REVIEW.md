# Discovery gap review (spec 0019)

Investigation of every sample resource the corrected engine (specs 0017–0018, code `b0c7f27`) does not ground.
Sample answers are used **only** to list the misses (evaluation tooling); the pipeline never reads them.
Reproduce: `python code/tools/discovery_report.py --split all --verbose --out <file>.json`
(PNG facts come from the cached Gemini extraction of all 11 screenshots, populated by this pass's live sample run;
an empty image cache is a different configuration).

## Outcome

**Investigation only — no additional defensible link was found, so no discovery rule was added.** Every miss lacks a
participant-visible, pre-cutoff record that ties the resource to the subject. Adding links from workflow timing,
same-file co-occurrence, numeric IDs or post-cutoff files would be guessing, which the contract forbids.

| Measure (32 samples) | Before (`b0c7f27`) | After (0019 tree) |
|---|---|---|
| Resource recall | 77/111 | 77/111 |
| Current-account linkage | 12/32 correct, 0 wrong (precision 12/12), 20 ungrounded | unchanged |
| Historical grounded accounts | 1 (case_17 `account_6523`, kept as an obligation; not in gold ⇒ counted as an extra) | unchanged |
| Other (non-account) resources | 65/79 | 65/79 |
| Extra grounded resources | 3 (`account_6523`, `tombstone_17` in case_17; `object_19` in case_07) | unchanged |
| Hit provenance | identifier 75, identifier+reference 1, reference 1 | unchanged |
| Full dataset (518 requests, no intent gate) | 167 grounded / 351 ungrounded accounts | unchanged |

The 0010 target of ≥ 85% sample resource recall remains **unmet** (77/111 = 69.4%). It is not redefined as achieved.

## Miss causes (34 misses)

Classified automatically by `discovery_report.miss_cause` from the evidence available at each case's `audit_at`
(first matching cause):

| Cause | Count | Meaning |
|---|---|---|
| `discovery_gap` | 0 | a subject identifier is parsed in an eligible record but did not link |
| `parser_gap_candidate` | 0 | a subject identifier appears in an eligible record's text but was not parsed |
| `linked_to_other_user` | 0 | eligible records name another known user |
| `eligible_records_without_ownership` | 12 | eligible records exist but carry no identifier/reference (404 `profile: null`, anonymized analytics) |
| `workflow_claims_only` | 14 | only operational activity claims (DELETE_RECORD) name the resource: ranked candidates, never grounded |
| `post_cutoff_evidence_only` | 5 | the resource appears only in files captured after `audit_at` |
| `no_participant_evidence` | 3 | no text/JSON/SQL/log/PDF/PNG record or activity names the resource |

## Gap table

| Case | Resource | Cause | Evidence checked / conclusion |
|---|---|---|---|
| case_01, 02, 07, 08, 10 | account_001/002/007/008/010 | workflow_claims_only | only DELETE_RECORD activity ("Deletion worker … Target resource: account_NNN"); no record with an identifier |
| case_09 | account_3960 | workflow_claims_only | DELETE_RECORD only before the cutoff; `evidence_06` (captured 09-18 > audit 09-16) names it with the subject's email — excluded by the cutoff |
| case_18, 20, 22, 23, 29, 30 | account_5521/5037/4990/410/7012/4163 | workflow_claims_only | DELETE_RECORD only |
| case_31, 32 | account_4857/8858 | workflow_claims_only | DELETE_RECORD only; case_31's absence is proven by the subject-scoped bundle `evidence_51`, but that does not link the account id |
| case_04 | account_004 | no_participant_evidence | no file, PNG or activity names it (`evidence_42` shows user_17's references without resource ids; `evidence_04` is post-cutoff) |
| case_21, 25, 26, 27, 28 | account_6440/3136/5684/3866/5482 | eligible_records_without_ownership | `evidence_92` `profile_lookups`: `status_code=404, profile=null`, no reference field; other records in the same file name the user, which is co-occurrence, not ownership |
| case_21, 25, 26, 27, 28 | analytics_5335/1895/4566/4574/6077 | eligible_records_without_ownership | `evidence_92` analytics profiles with `customer_reference`, email, phone and hash all null |
| case_03 | analytics_9406 | eligible_records_without_ownership | `evidence_94` trace `rb-095409-021`: `lookup_key=null`, all identifiers null; the subject's own traces in that file are separate trace groups |
| case_04 | analytics_901 | eligible_records_without_ownership | `evidence_56` export record with identifiers null |
| case_09, 23, 24, 29, 30 | audit_record_4902/4128/7095/3954/1707 | post_cutoff_evidence_only | first named (with the subject's user_id) in files captured after `audit_at`; `evidence_37` (eligible) shows only user_03's audit_record_001–006 |
| case_18, 20 | audit_record_6645/5569 | no_participant_evidence | not named in any evidence file or activity row |

## Searches performed

- All non-`resource_id` fields holding resource-id-shaped values across the ledger: only `source_resource_id`
  (already a reference edge), self-references (`archive_key`, `object_key`, search hits) and activity details.
- All activity types: only `LINK_RESOURCE_IDENTITY` details carry identifiers (already used); DELETE/ANONYMIZE
  details name only the resource.
- `user_audit_log.csv` ids (`audit_NN`) are unrelated to `audit_record_*` resources.
- Raw-text check of every eligible record of a missed resource for the subject's emails, phones, hashes and user_id
  (`parser_gap_candidate`): none.

## Guards (tests)

`code/tests/test_grounded_discovery_regressions.py` adds the guards not already in `test_discovery.py`: a 404
null-profile lookup and an anonymized record do not ground; same-file co-occurrence is not ownership; repeated
requests of one subject (case_52 → case_33) use their own cutoffs. Existing tests keep the decoy-name, post-cutoff,
historical-account and ungrounded-never-named guards.
