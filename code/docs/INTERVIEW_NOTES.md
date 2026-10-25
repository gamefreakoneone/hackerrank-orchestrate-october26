# Interview notes — Ghost Data Still Exists

## 1. Architecture in one paragraph

**Code decides, models read.** A deterministic Python engine (`code/ghostaudit/`) owns identity, evidence parsing,
discovery, state at `audit_at`, policy, the COMPLETE/INCOMPLETE decision, step generation, citation and ordering. Models
are called at three bounded points through one shared layer (`ghostaudit/llm/`: cache → call → pydantic validation →
one repair retry → usage ledger) and only return typed facts:

| Point | Model | Returns | Calls in the final run |
|---|---|---|---|
| Request intent | TypeSafe Jev (Choice), Azure gpt-6-luna adjudicates disagreements | label in DELETION/ACCESS/CORRECTION/EXPORT/OPT_OUT/OTHER | 518 Jev + 3 Azure |
| PNG screenshots | Gemini 3.8 Flash via Strands | `VisionRecord` rows, regex/identity revalidated | 11 |
| Category fallback (no record field/table/event maps the resource) | Jev (Choice) | one of the data categories, accepted at p ≥ 0.5 | 3 |

Pipeline per request: intent gate → identity at the cutoff → exact-identifier discovery + grounded account link →
state per resource → policy obligations → plan → canonical serialization → validator.

## 2. Investigation approach

- **Strict cutoff.** A file counts only if its manifest `captured_at ≤ audit_at` (lines inside a later file are ignored
  even when dated earlier); activity and audit rows by `event_time`. Post-cutoff identity values are never read.
- **Identity.** Current snapshot (if updated before the cutoff) + every pre-cutoff audit value; sha256 of every email;
  exact per-type matching (emails/hashes case-insensitive, phone digits, NFC names). A **name never links on its own**
  (decoys: "Jonas Berg" vs "Jonas Berglund").
- **Evidence ledger.** SQL snapshots (primary/replica tables, generic stores with `record_json`), JSON exports and
  snapshot bundles, six log formats grouped by trace id (the lookup key and the resource id sit on different lines),
  a handover text, PDFs and vision rows become `Observation`s; full tables/collections also become
  `SnapshotCoverage` (an empty collection still proves absence).
- **Grounded account link.** An account belongs to the subject only if one eligible record carries a subject identifier
  and the account id (readback trace, export lookup with a profile, history `record_lookup`, catalog link, reference
  edge). Workflow timing only **ranks** candidates for diagnostics. 20/32 samples (342/508 deletion requests in the
  corrected run) have no grounded link: they carry `ACCOUNT_UNGROUNDED` and can never be COMPLETE.
- **State, per storage copy (0017).** Only SQL table names identify copies (primary, failover/read/reporting/regional
  replicas); exports, bundles, service reads, screens and documents read the system of record. Per copy the latest
  observation wins by observation time (snapshot header, read/log time, record time; file capture time only gates
  eligibility); a copy last seen present is cleared only by a later snapshot of that same copy. Any violating copy
  makes the obligation unsatisfied and is the cited proof, so a newer primary 404 can no longer hide a replica.
  Records-assurance bundles list ~10 subjects each, so their omissions count only for those subjects. A never-observed
  resource keeps the omission rule (latest replica-covering snapshot after the last DELETE claim, else latest, else
  UNKNOWN); state-check activity is a last resort; operational claims never set state.
- **Preservation (0018).** REDACT / ANONYMIZE / RETAIN keep the record: absence never satisfies them, a tombstone must
  keep the subject's user_id, and a missing kept record raises `REQUIRED_RECORD_MISSING` (no invented finding).

## 3. Remediation planning

Templates per required end state (from `deletion_rules.csv`): DELETE → report remaining / delete / verify absent;
REDACT (incl. tombstones: user_id may remain) → report exposed PII / redact / verify redacted; ANONYMIZE (no user link
either) → … / anonymize / verify anonymized; RETAIN → verify present; backups → report restore risk / block restore /
verify blocked; data flows → report active flow / disable / verify disabled. Canonical order `(OP_ORDER, system,
resource)` puts disabling flows and blocking restores before record changes. INCOMPLETE ⇒ findings (cited) +
remediation (`""`) for violations with known state, verification (`""`) for every obligation. COMPLETE ⇒ verification
only, each citing the evidence that established the state. Conditions are tri-state: an expired retention date makes the
RETAIN condition FALSE ⇒ `POLICY_UNDEFINED`, no invented DELETE.

## 4. Walkthrough: case_11 (matches the sample answer exactly)

Request: "I would like the account associated with this address to be erased…", email `novak.tomasz@icloud.com`,
reported COMPLETE, audit_at 2026-10-01T12:00Z.

1. **Intent:** Jev → DELETION (p = 1.0), keyword check agrees → accepted.
2. **Identity:** `user_32` from the current snapshot; identifiers = email, phone, name, user id, email hashes.
3. **Discovery:** the shift handover `evidence_03` (captured 2026-10-01T12:00Z, eligible) lists rows with the subject's
   email: `account_4248` (USER_PROFILE, NOT_FOUND), `search_052` (FOUND), `analytics_2034` (IDENTIFIABLE),
   `support_864` (IDENTIFIABLE), `data_flow_9522` (ACTIVE); the audit record `audit_record_9394` is linked by user id.
   The account link is grounded (email + account id in one row).
4. **State and policy:** account ABSENT (required ABSENT ✓); search entry PRESENT (DELETE ✗); analytics still
   identifiable (ANONYMIZE ✗); support message identifiable (REDACT ✗; condition defaulted); connector ACTIVE (must be
   DISABLED ✗); audit record PRESENT (RETAIN ✓).
5. **Plan (14 steps):** 4 findings citing `evidence_03` → DISABLE_DATA_FLOW first, then DELETE search_052, REDACT
   support_864, ANONYMIZE analytics_2034 → 6 verifications (one per obligation) with empty evidence ids.

## 5. Evaluation (samples are an inspected regression set, not a holdout)

| | Status | Account linkage | Step F1 | Sequence exact |
|---|---|---|---|---|
| all 32 samples | 23/32 (0.719) — equals the pre-registered conditional bound | 12/32 correct, 0 wrong | 0.896 (P 0.981, R 0.824) | 9/32 |
| dev 20 / holdout 12 | 0.750 / 0.667 | 7/20 / 5/12 | 0.900 / 0.889 | 5/20 / 4/12 |

(Corrected code `b90914b`, cached responses of a live run; the overnight figures were F1 0.898 from different live
provider responses.)

- Every status miss is a gold-COMPLETE sample without a grounded account (we refuse to name a guessed account). 9 of the
  12 grounded samples have an exactly matching plan (an earlier report wrongly said all). Oracle-assisted component
  check (given the gold resources): 103/111 states and 75/75 citations. End-to-end discovery: 77/111 resources (the
  0010 ≥85% target is unmet; `DISCOVERY_GAP_REVIEW.md`).
- Custom validation: 8 cases / 9 requests (historical email + decoy, post-audit evidence, German access request,
  tombstone + active sync, retained backup, expired retention, repeated request, ungrounded account) — expected outputs
  committed before running; 9/9 pass. Four metamorphic tests pass.
- Ablations: no model 21/32; no history 22/32; trust claims 23/32; ranked guessed accounts raise sequence exact to
  12/32 but guesses are wrong 12/20 times — kept out of the submission.
- Corrected final cold run `0021_candidate_20261025T104010Z` (code `b90914b`): 518 rows, INCOMPLETE 459 / COMPLETE 49 /
  NOT_APPLICABLE 10, validator 0 errors / 105 blocker warnings; 535 model calls, 273k input / 92k output tokens,
  estimated $0.24 (unverified third-party prices). Versus the overnight output 4 rows changed: case_86 and case_390
  become COMPLETE (a later NOT_FOUND read of the same copy supersedes an earlier FOUND), case_33 drops an export a later
  full snapshot omits, case_61 gets an UNKNOWN_STATE obligation because the live category fallback answer changed.

## 6. Failures found and fixed

1. Cache-miss lines inside a trace were read as "record absent" → infrastructure lines excluded.
2. Readback `*_read_completed` events were not counted as presence → fixed (state agreement 99 → 104/111).
3. A later primary-only inventory overrode a replica that still held the account (case_05 replica drift) → an omission
   must cover the replica where the record was last seen.
4. Generic snapshots claimed coverage of collections they never held → coverage limited to collections in the file.
5. Negated requests contain deletion words → keyword check is only a cross-check; Azure adjudicates disagreements.

Corrective pass after an independent review (specs 0017–0021):

6. A newer primary-only 404 or clean record could clear an uncleared replica (false COMPLETE) → state per copy.
7. Absence satisfied REDACT / ANONYMIZE / retained-backup obligations (false COMPLETE) → separate preservation check.
8. 34 sample misses investigated: none has a pre-cutoff record tying it to the subject → no new link rule (honest gap).
9. The report claimed every grounded sample was exact (9 of 12 are) and read ignored `runs/` files → reports are built
   from a hashed evaluation bundle without model calls and fail on any mismatch.
10. `main.py` overwrote the selected output before validating → candidate-first publication and a release finalizer.

## 7. Known limits / what I would do next

- Grounded linkage is the binding constraint (166/508 deletion requests in the corrected run). More grounded sources would raise status
  accuracy directly; the evidence currently offers none for the remaining accounts, so they stay INCOMPLETE.
- Anonymized analytics records linked only through workflow claims are not discovered (same rule).
- The absence rule was chosen on four sample citations; the moved-file metamorphic test documents its replica preference.
- Model answers at the bounded points are not perfectly repeatable across live runs (case_61's category fallback; Gemini
  output-token counts); every run's ledger and diagnostics record what was actually returned.
- A run reads the Git revision when it writes its manifest: do not commit while a run is in flight.
