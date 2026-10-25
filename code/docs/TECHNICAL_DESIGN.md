# TECHNICAL_DESIGN — Ghost Data Still Exists

Binding design for the deletion-audit agent. `HANDOFF.md` is the planning brief; this file is the
current truth. Change a Key Contract only through a spec that says so, and record it in the
Decision log.

## 1. Principle

**Code decides, models read.** A deterministic Python engine owns identity resolution, evidence
parsing, resource discovery, state at `audit_at`, policy application, the completeness decision,
step generation, evidence citation, ordering and serialization. Models are called only at
bounded points and return validated typed facts:

| Point | Model | Output type |
|---|---|---|
| Request intent (multilingual) | TypeSafe Jev (`JEV_MODEL`), Azure fallback | enum `DELETION / ACCESS / CORRECTION / EXPORT / OPT_OUT / OTHER` + confidence |
| PNG evidence (11 files) | Gemini (`GEMINI_VISION_MODEL`) via Strands | list of `VisionRecord` (see §3.3), regex-revalidated |
| Category fallback (only when no explicit field/event/table maps it) | Jev choice | enum of the 15 `data_category` values |

## 2. Pipeline

```
dataset/*.csv ─► loaders (typed, tz-aware UTC)
dataset/evidence ─► parsers (once per file, cached by sha256 + parser version)
    sql (sqlite3 :memory:) · json · logs (6 formats, grouped by trace_id) · txt · pdf (pypdf) · png (vision)
    └─► Observation ledger + inverted index (identifier → obs, resource_id → obs)
per case:
  1 intent gate ─ not deletion → NOT_APPLICABLE, []
  2 identity resolver: current snapshot + audit rows with event_time ≤ audit_at (post-cutoff rows never read)
  3 discovery: exact identifier-linked records (≤ audit_at) → fixed-point expansion
              + subject-level account link (§5 Q3): grounded reference links; workflow timing only ranks
                ungrounded candidates (diagnostics), never grounds them
  4 state @ audit_at per resource: latest establishing observation or SnapshotCoverage (file captured_at ≤ audit_at);
    state-check activity (CHECK_DATA_FLOW / CHECK_RESTORE_ACCESS) only if no file establishes it;
    operational claims (DELETE_RECORD SUCCESS, …) never set state; nothing establishes it ⇒ UNKNOWN
  5 policy → obligations (required end state; rule conditions TRUE/FALSE/UNKNOWN)
  6 status = no completion blocker ∧ ≥1 obligation ∧ all satisfied ? COMPLETE : INCOMPLETE (§3.5)
  7 planner: findings + remediation (INCOMPLETE) + verification for every obligation
  8 citation (§5 Q2: establishing file; activity/audit id fallback) → canonical sort → validator → output.csv
    + diagnostics (flags) per case
  usage ledger → evaluation/usage_report.md
```

## 3. Key Contracts

### 3.1 Step (output) — `ghostaudit/models.py`

```python
class Step(BaseModel, frozen=True):
    step_no: int                      # 1..n consecutive
    phase: Literal["FINDING", "REMEDIATION", "VERIFICATION"]
    system_id: str                    # logical service, e.g. "account_service"
    resource_id: str                  # e.g. "account_005"
    operation: Operation              # enum, AGENTS.md §6.4 (15 values)
    state: State                      # fixed by operation (OP_STATE table)
    evidence_id: str                  # file_id, or "" for remediation / future verification
```

`OP_ORDER` (sort rank) is the operation table order in `problem_statement.md`:
REPORT_REMAINING_RECORD, REPORT_EXPOSED_PII, REPORT_ACTIVE_DATA_FLOW, REPORT_RESTORE_RISK,
DISABLE_DATA_FLOW, BLOCK_RESTORE, DELETE_RECORD, REDACT_RECORD, ANONYMIZE_RECORD,
VERIFY_RECORD_ABSENT, VERIFY_RECORD_PRESENT, VERIFY_RECORD_REDACTED, VERIFY_RECORD_ANONYMIZED,
VERIFY_DATA_FLOW_DISABLED, VERIFY_RESTORE_BLOCKED.

Canonical sort key: `(OP_ORDER[op], system_id, resource_id)`. Phase order is implied by
OP_ORDER. Verified on 32/32 samples (DATA_NOTES §10).

Serialization: `json.dumps(steps, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`.
Rows sorted by the integer suffix of `case_id`.

### 3.2 Observation (evidence ledger) — `ghostaudit/evidence/model.py`

```python
class Observation(BaseModel, frozen=True):
    evidence_id: str                  # file_id (evidence_NN); activity_id when source_kind == "activity"
    captured_at: datetime             # manifest captured_at; activity event_time for activity — the cutoff key
    observed_at: datetime | None      # record-level time if present (observed_at, updated_at, log ts)
    source_kind: Literal["sql", "json", "log", "txt", "pdf", "png", "activity"]  # "activity" = state-check events only
    container: str                    # table / collection / log service / document type
    physical_copy: str                # e.g. "customer_profiles_failover_replica", "primary"
    system_id: str | None             # logical service (derived, §5 Q1)
    resource_id: str
    category: str | None              # data_category (derived, §5 Q1)
    identifiers: frozenset[str]       # emails, phones, names, hashes, user_ids found in the record
    fields: Mapping[str, str | None]  # normalized: status_code, enabled, restore_allowed,
                                      # retention_until, event, matched_value, ... (None = null)
```

One record = one SQL row, one JSON object carrying a `resource_id`, one log **trace_id group**
(or single line without trace_id), one PDF, one PNG row extracted by vision.

### 3.3 SnapshotCoverage (absence evidence) — `ghostaudit/evidence/model.py`

Separate from `Observation` because an empty table/collection has no record but still proves absence.

```python
class SnapshotCoverage(BaseModel, frozen=True):
    file_id: str
    captured_at: datetime             # manifest captured_at (cutoff key); snapshot-level time kept in `snapshot_at`
    snapshot_at: datetime | None      # "Captured at" header / snapshots[].captured_at / snapshot_scope.captured_at
    system_id: str                    # logical service (account_service, …)
    collection: str                   # table or collection, e.g. "customer_profiles_failover_replica"
    physical_copy: str                # "primary", "failover_replica", "read_replica", "replica_eu_west", "bundle", …
    scope: str                        # what the snapshot claims to cover: "full_table", or the
                                      # snapshot_scope origin_system list for inventory files
    row_count: int                    # 0 is valid and meaningful (evidence_51, evidence_90)
    resource_ids: frozenset[str]
```

Emitted for complete SQL tables, generic-store collections (`customer_data_*` × `collection_name`), inventory
tables under `snapshot_scope`, and bundle `snapshots[]` entries. Never for `service_resource_export` lookups,
logs, PDFs or PNGs (those observe specific resources only).

### 3.3b VisionRecord (LLM output, PNG only)

```python
class VisionRecord(BaseModel):
    resource_id: str          # must match RES_RE after extraction, else dropped
    system_hint: str | None
    record_type: str | None
    subject_identifiers: list[str]   # each must regex-validate as email/phone/user_id/hash
    status_text: str | None          # e.g. "Enabled", "Restore allowed", "Valid"
    timestamp: str | None
```

### 3.4 Obligation — `ghostaudit/obligations.py`

```python
class Obligation(BaseModel, frozen=True):
    system_id: str
    resource_id: str
    category: str                     # data_category or "DATA_FLOW"
    required: Literal["ABSENT", "REDACTED", "ANONYMIZED", "PRESENT", "DISABLED", "BLOCKED"]
    current: Literal["PRESENT", "EXPOSED", "ACTIVE", "ABSENT", "REDACTED", "ANONYMIZED",
                     "DISABLED", "BLOCKED", "UNKNOWN"]
    condition: Literal["TRUE", "FALSE", "UNKNOWN"]  # rule condition at audit_at; UNKNOWN ⇒ default branch, flagged;
                                      # FALSE ⇒ no rule-defined action ⇒ POLICY_UNDEFINED blocker (§3.5)
    proof: str                        # establishing file_id (preferred) or activity_id/audit_id fallback, or ""
    proof_kind: Literal["file", "activity", "audit", ""]
    satisfied: bool                   # False whenever current == "UNKNOWN"
```

Templates (from rules + gold):

| required | violation finding | remediation | verification |
|---|---|---|---|
| ABSENT (DELETE) | REPORT_REMAINING_RECORD | DELETE_RECORD | VERIFY_RECORD_ABSENT |
| REDACTED (REDACT, incl. tombstone) | REPORT_EXPOSED_PII | REDACT_RECORD | VERIFY_RECORD_REDACTED |
| ANONYMIZED | REPORT_EXPOSED_PII | ANONYMIZE_RECORD | VERIFY_RECORD_ANONYMIZED |
| PRESENT (RETAIN audit / legal hold) | — | — | VERIFY_RECORD_PRESENT |
| BLOCKED (BACKUP_ARCHIVE) | REPORT_RESTORE_RISK | BLOCK_RESTORE | VERIFY_RESTORE_BLOCKED |
| DISABLED (active data flow) | REPORT_ACTIVE_DATA_FLOW | DISABLE_DATA_FLOW | VERIFY_DATA_FLOW_DISABLED |

Planner: INCOMPLETE ⇒ findings + remediation for unsatisfied obligations with known state (cited /
empty), verification for **every** obligation with `evidence_id=""`. COMPLETE ⇒ verification only, each
citing its `proof`.

### 3.5 Completion blockers and diagnostics

A case is COMPLETE only if no blocker fires, there is ≥1 obligation, and every obligation is satisfied with
proof. Exact output per flag (written to `runs/<run>/diagnostics.jsonl`, counted by the scorer report):

| Flag | When | Status | Steps |
|---|---|---|---|
| `ACCOUNT_UNGROUNDED` | no grounded subject→account link (§5 Q3); covers "no candidate at all" | INCOMPLETE (blocker) | **no account steps**; ranked candidates go to diagnostics only (ablation `--ungrounded-account-steps ranked` in 0015 measures emitting the top candidate instead) |
| `ACCOUNT_MULTI_GROUNDED` | >1 grounded account | not a blocker | the most recent grounded link is the **current** account; every older grounded account stays an obligation (**historical account**, may still retain data) unless evidence excludes it (linked to another user, or proven the same record); never dropped silently |
| `UNKNOWN_STATE` | no eligible file / coverage / state-check activity establishes the state | INCOMPLETE (blocker) | no finding, no remediation for it; VERIFICATION step (required end state) with `""` |
| `POLICY_UNDEFINED` | a rule condition evaluates FALSE (the rules define no action for that branch) | INCOMPLETE (blocker) | no step for that resource; flagged for review — code does not invent an action |
| `EMPTY_OBLIGATIONS` | deletion authorized but nothing discovered | INCOMPLETE (blocker) | `[]` |
| `CONDITION_DEFAULTED` | rule condition has no field (UNKNOWN) | not a blocker | default (rule's stated) branch |
| `ACTIVITY_CITATION` | proof is a state-check activity_id / audit_id | not a blocker | cited as is |
| `IDENTITY_SNAPSHOT_AFTER_CUTOFF` | subject's identity snapshot updated_at > audit_at | not a blocker | snapshot values are **excluded** (unavailable at the cutoff); identifiers come only from pre-cutoff audit rows and user_id; a request email not found there leaves the subject as that email + hash; flagged (0/550 occurrences) |

No finding, account or evidence is ever invented to fill a blocker. Proving an account deleted does not prove it
is the subject's account, so a ranked (ungrounded) account can never support COMPLETE. The validator accepts
"INCOMPLETE without findings" and "INCOMPLETE with `[]`" only when a blocker flag is present (warning); `[]`
otherwise requires NOT_APPLICABLE.

Phase-0c measurement on samples (`p0_q3c_account_link.py` §F, gold as oracle). **Linkage accuracy is reported
separately from status accuracy:** grounded links 12/32 (11 unique, 1 multi-grounded: current = most recent link, older kept as historical),
0 wrong; ungrounded 20/32 (the top-ranked candidate would be right 8/20, wrong 12/20 = 60% of ambiguous cases,
37.5% of all samples). Cost of the grounding requirement: 9 of 10 gold-COMPLETE samples have no grounded link and
become INCOMPLETE, so 23/32 (≈71.9%) is a **conditional upper bound** on sample status under current linking —
not a measured pipeline accuracy and not a dataset ceiling; it rises as spec 0010 grounds more accounts. We accept
that cost rather than claim COMPLETE on an unproven identity link. `UNKNOWN_STATE` over gold resources: 8/111
(7 retained audit records in INCOMPLETE cases; account_004 in case_04 is a linking gap, since evidence_54 covers it).

### 3.6 Provider interface — `ghostaudit/llm/`

```python
class StructuredCall(Protocol):
    def __call__(self, *, task: str, schema: type[BaseModel], inputs: dict,
                 images: list[Path] = ()) -> BaseModel: ...
```

Every call: cache lookup (key = sha256 of task, model, schema JSON, canonical inputs, image
hashes) → model call (temperature 0 where accepted) → pydantic validation → one repair retry →
usage ledger row `{provider, model, task, input_tokens, output_tokens, cached, latency_ms}`.
Providers: `jev` (typesafe-sdk), `azure` (Strands `OpenAIModel`, `base_url=AZURE_OPENAI_ENDPOINT`),
`gemini` (Strands `GeminiModel`). Env vars: `TYPESAFE_API_KEY`, `TYPESAFE_API_BASE`, `JEV_MODEL`,
`JEV_CONFIDENCE_THRESHOLD`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`,
`AZURE_DEPLOYMENT_FALLBACK`, `GEMINI_API_KEY`, `GEMINI_VISION_MODEL`. `--offline` runs with
cache only and deterministic fallbacks (keyword intent, no PNG facts).

### 3.7 CLI

```
python code/main.py [--cases sample|all] [--out PATH] [--offline] [--no-cache] [--case case_NN ...]
```

Default `--cases all --out <repo>/output.csv`. `--cases sample` reads
`sample_deletion_requests.csv`. Exit code ≠ 0 if the validator fails. `sample_output.csv` is read
only by `code/evaluation/`, never by `ghostaudit/`.

## 4. Repo layout

As HANDOFF §5, plus `code/tools/` (Phase-0 analysis scripts `p0_*.py`, provider smoke test).

## 5. Data-derived decisions (Phase 0, corrected in Phase 0b)

Scripts: `code/tools/p0_q2_evidence_selection.py`, `p0_q2b_coverage.py`, `p0_q3_discovery.py`,
`p0_q3c_account_link.py`, `p0_q1_q5_categories.py`. All numbers are on the 32 samples (111 gold resources,
75 cited steps). Phase 0b (after the Codex review `code/docs/reviews/0000b-codex-phase0-review.md`) made every
measurement cutoff-safe (files by manifest captured_at, activity and audit rows by event_time, all ≤ audit_at)
and replaced substring matching with exact identifier matching. Phase 0c (after a second review of `d440ced`)
made identity strict (post-cutoff audit rows are never read), replaced the unreproducible absence rule with an
executable check, required grounded account links for COMPLETE, and corrected the policy and evaluation wording.

**Evaluation honesty.** Every sample answer was inspected to make these decisions, so the 32 samples (and any
dev/holdout split of them) are a **regression set**, not untouched validation. Spec 0014's synthetic cases and
metamorphic tests are **custom and metamorphic validation**: they are designed around known risks and will be
used to fix the system, so they are not a holdout either. No untouched holdout exists; reports must say so. All
rules below are fitted to samples; small counts (e.g. 4/4) are hypotheses that the full run keeps checking via
diagnostics.

### Q1 — Where does `data_category` come from?

Explicit fields first, then container names, then log event names; LLM only as fallback.

- `record_type` field (JSON, logs, txt handover): values seen USER_PROFILE 88, SECURITY_AUDIT_LOG 80,
  SEARCH_INDEX_ENTRY 48, SUPPORT_MESSAGE 26, ANALYTICS_PROFILE 25, DATA_FLOW 25, BACKUP_ARCHIVE 8,
  USER_EXPORT 3, LEGAL_HOLD_RECORD 1.
- Tables/collections map 1:1: `customer_profiles*` → USER_PROFILE, `customer_search_documents`/
  `search_documents_primary` → SEARCH_INDEX_ENTRY, `support_conversations`/`support_records` →
  SUPPORT_MESSAGE, `ticket_attachments` → SUPPORT_ATTACHMENT, `customer_analytics_*` →
  ANALYTICS_PROFILE, `customer_export*` → USER_EXPORT, `backup_*`/`backup_catalog` → BACKUP_ARCHIVE,
  `connector_*` → DATA_FLOW, `security_audit_*` → SECURITY_AUDIT_LOG, `retained_order_records` →
  LEGAL_HOLD_RECORD, `deleted_customer_references` → ACCOUNT_TOMBSTONE.
- Log event names: `profile_lookup_completed` → USER_PROFILE, `index_query_completed` → SEARCH,
  `message_pii_scan`/`message_read` → SUPPORT_MESSAGE (REDACT), `attachment_pii_scan` →
  SUPPORT_ATTACHMENT (DELETE), `analytics_identity_scan`/`analytics_profile_read` → ANALYTICS_PROFILE,
  `contact_lookup_completed` (analytics, `email_opt_in`) → DELETE (gold case_12 analytics_9914),
  `connector_heartbeat`/`connector_config_loaded` → DATA_FLOW, `restore_candidate_evaluated`/
  `restore_authorization_completed` → BACKUP_ARCHIVE, `audit_record_read_completed` → SECURITY_AUDIT_LOG,
  `export_download_check_completed` → USER_EXPORT. Support replica `legacy_contact_index` → DELETE
  (gold case_10 support_002).
- Gold confirms the same prefix can take different actions: analytics ANONYMIZE 12 vs ABSENT 1;
  support REDACTED 8 vs ABSENT 3. Category comes from the record, not the system.
- Resource prefix → logical `system_id` (gold): account→account_service, search→search_service,
  support→support_platform, analytics→analytics_platform, export→export_service,
  data_flow→integration_service, backup→backup_service, tombstone→identity_service,
  audit_record→security_service, legal_hold→legal_service (no sample).

### Q2 — Which file does gold cite?

- **71/71** cited steps whose resource_id appears in some eligible text file cite the **latest file (manifest
  `captured_at`) ≤ audit_at that mentions the resource**. 0/75 cite a file captured after audit_at. This is a
  heuristic fit, not a proven state-reconstruction rule.
- The remaining **4/75** are VERIFY_RECORD_ABSENT for accounts **not mentioned** in the cited file; the file is a
  snapshot whose account table/collection omits the account (case_01/02/04 → `evidence_54`, case_31 →
  `evidence_51`, whose account `customer_profiles` collection is **empty**). This needs a coverage record that
  exists even with zero rows → `SnapshotCoverage` (§3.3).
- **Citation rule = latest eligible file that ESTABLISHES the required state for that system**
  (`p0_q2b_coverage.py`, 4/4 omission citations):
  1. observed state: latest eligible observation of the resource showing the state (the 71/71 rule);
  2. absence by omission (`p0_q2b_coverage.py`, executable, asserts the chosen rule): candidates are eligible
     `SnapshotCoverage` rows of the system that do not contain the resource. Definitions: **scope** = the
     system's profile table/collection in that file; **observation time** = manifest captured_at; **replica
     coverage** = the file covers ≥1 non-primary physical copy (failover/read/reporting/regional replica);
     **superseded** = captured at or before the resource's last DELETE_RECORD activity ≤ audit_at (cannot prove the
     deletion took effect). Rule: drop superseded candidates; among the rest take the **latest with replica
     coverage**, else the latest; **if no candidate survives, nothing establishes absence ⇒ UNKNOWN_STATE** (no
     fallback to superseded snapshots — asserted with a counterexample in the script). Results of every rule tried
     (4 omission citations):
     latest 3/4 (case_04 → evidence_90); latest-after-delete 3/4; the 0b "most copies, then latest" claim **3/4**
     (case_04 → evidence_29, three copies on 05-19 — the 0b 4/4 claim did not reproduce because the old script
     printed only the latest four candidates); latest-with-replica-after-delete **4/4**. The last was chosen
     **post hoc** on these 4 points; rationale: case_05 shows replica drift (primary empty, failover replica
     holds the account), so a primary-only snapshot (evidence_90) cannot establish absence when a replica-covering
     snapshot exists; case_31's account was deleted 09-06, superseding evidence_54/evidence_90, and no later
     snapshot covers a replica, so the latest (evidence_51, empty collection) is cited. Treat as a hypothesis.
  3. fallback when no file establishes the state: a **state-check** activity ≤ audit_at — `CHECK_DATA_FLOW`
     ("confirmed that data flow X remains enabled") or `CHECK_RESTORE_ACCESS` ("confirmed that archive X can still
     be restored") — or an `audit_id` for an identity value, flagged `ACTIVITY_CITATION`. Operational claims
     (DELETE/REDACT/ANONYMIZE/BLOCK_RESTORE/DISABLE_DATA_FLOW/RETAIN/SYNC/INDEX/UPDATE/CREATE_EXPORT/SEND_EMAIL/
     REFRESH_CACHE/CLASSIFY_REQUEST/RESTORE_BACKUP results) are **claims**: they add candidates and risks
     (RESTORE_BACKUP names a repopulated resource) but never establish a state and are never cited as proof.
     The participant contract allows activity/audit citations; samples never needed them.
- Cutoff is by file `captured_at`, not line timestamps: `evidence_06` (captured 2026-09-18) has lines dated
  2026-09-16 that would prove case_09 facts, and gold does not use it.

### Q3 — Does identifier search + expansion find the gold resources?

Cutoff-safe, exact matching (`p0_q3_discovery.py`): emails, user_ids and sha256 hashes compared as whole tokens;
names and phones must not be embedded in a longer word/number.

- Identifier co-occurrence in one record (SQL row / JSON object / **log trace_id group** / PDF / txt row) plus
  LINK_RESOURCE_IDENTITY finds **77/111** gold resources with **3** extra candidates (Phase 0 substring matching
  reported 45 extras: the old numbers did not validate exact matching). Trace grouping is required: readback
  logs put `lookup_key=<email>` on the `*_started` line and `resource_id` on the `*_completed` line.
- Decoys that exact matching rejects: `Jonas Berglund` vs `Jonas Berg`, `Mateo Rios Gil` vs `Mateo Ríos`.
- Misses are dominated by resources whose identifiers were already removed: deleted accounts (`profile: null`,
  status 404) and anonymized analytics (`customer_reference: null`).
- **Account linking** (`p0_q3c_account_link.py`). Every sample case has exactly one account_service resource.
  - A. Phase-0 heuristic re-run cutoff-safe (window upper bound `min(audit_at, reported_at + 15 min)`):
    identifier-owned correct **12/32** (was 15/32 with future leakage; lost case_09, case_26, case_27), unique
    unowned 2, ambiguous 18. (The review measured 12 / 1 / 19 with substring matching.)
  - B. Subject-level linking. **Grounded** = a subject identifier and the account id in one record ≤ audit_at
    (pre-deletion rows, customer/subject_reference, LINK_RESOURCE_IDENTITY, readback trace groups). Grounded:
    **11** unique + **1** multi-grounded (case_17: account_6523 from a 03-10 readback 404, account_4092 from a
    09-15 readback; the most recent grounded link is the current account and matches gold — one data point;
    measured by link time, not workflow timing), **0 wrong**. account_6523 stays a historical-account obligation
    (its 03-10 readback 404 would prove ABSENT); gold lists only account_4092, so this costs one extra step on
    case_17 — accepted, because a newer link does not prove the older account holds no data.
    **Ungrounded: 20/32.** Workflow candidates (DELETE_RECORD → account_service in the request window, not linked
    to another user) are only ranked: nearest to reported_at 8/20, claim-aware nearest 8/20, latest before
    reported_at 5/20, earliest after request 2/20, unique-candidate-only 2/20. The best ranking is wrong on 12/20
    (60%) ambiguous cases, 37.5% of all samples, and 7 of the 9 gold-COMPLETE cases that would rely on it get the
    wrong account id. **Decision (0c): a ranked candidate never grounds the subject's account**; it is reported in
    diagnostics and the case carries the `ACCOUNT_UNGROUNDED` blocker (§3.5). Linkage accuracy is a separate
    metric from status accuracy in every report. Raising grounded linkage above 12/32 is spec 0010's main goal.
  - No one-to-one constraint: unique account ownership does not imply unique request ownership. The evaluation
    set has **1 subject with 2 requests (case_33, case_52)**; linking is per subject, with per-request cutoffs.
  - Tombstones carry `subject_reference` (user_id) but no account id: they confirm the subject, not the account.
- **Ceiling under the cutoff rule (text + CSV only):** of 111 gold resources, 89 appear in a pre-audit text file,
  14 only in pre-audit activity, **8 in neither**: account_004 (case_04) and audit_record_4902/6645/5569/4128/
  7095/3954/1707. PNG contents were **excluded** from this count, so it is not a proven ceiling. Spec 0009 must
  check `evidence_37` security_audit_explorer_20260905.png (eligible for all 7 audit-record cases; the visible
  table shows only user_03's audit_record_001–006) and `evidence_42` deleted_account_reference_20260310.png for
  account_004 (`evidence_04` account_admin_console_20260926.png is after case_04's cutoff).
- **Spec 0009 PNG check (overnight run):** all 11 PNGs extracted (Gemini, cached, regex-revalidated). `evidence_37` shows only
  user_03's audit_record_001–006; `evidence_42` shows user_17's order/support/finance references and no resource id. None
  of the 8 resources appears in any PNG row, so the text+CSV+PNG reach stays **103/111** (89 text + 14 activity-only).

### Q4 — How is COMPLETE proven for flows and backups?

`service_resource_export` JSON (`evidence_92` style) per-service collections:
`integration_service.connectors[].enabled=false`, `backup_service.restore_entries[].restore_allowed=false`,
`account_service.profile_lookups[].status_code=404, profile=null`, analytics profiles with all
identifier fields null, `security_service.audit_records[].retention_until`. Readback logs give the same
facts per trace (`enabled=`, `eligible=`/`deletion_block=`, `http_status=404`). Active risk evidence:
`enabled=true`, `restore_allowed=1`/`eligible=true deletion_block=false`, CHECK_DATA_FLOW /
CHECK_RESTORE_ACCESS activity (claims; used for discovery and timeline, cited only as the §Q2 fallback).

### Q5 — Condition-failure branches?

- `retention_until`: 4 distinct values, 2031-12-31 … 2034-09-30, all later than every audit_at (max 2026-10-01).
- No shared-attachment / other-customer / hold-released signals in any file.
- Legal holds exist (`legal_hold_*`, 7 files, `retained_order_records`) but none in sample gold.
- ⇒ Conditions are **tri-state** (TRUE / FALSE / UNKNOWN), evaluated at audit_at where a field exists:
  SECURITY_AUDIT_LOG `retention_until ≥ audit_at`; LEGAL_HOLD_RECORD hold active per the register / hold fields.
  TRUE ⇒ the rule's action. UNKNOWN (no field) ⇒ the rule's action, flagged `CONDITION_DEFAULTED`. **FALSE ⇒ the
  supplied rules define no action** (they state conditional RETAIN/REDACT/… only), so code does **not** infer an
  inverse such as DELETE: the resource gets the `POLICY_UNDEFINED` blocker and no step (§3.5). 0c correction of 0b,
  which had assumed expired retention ⇒ DELETE.
- BACKUP_ARCHIVE "restore access can be blocked": `restore_allowed=false` is the resource **state** BLOCKED
  (obligation satisfied), not the condition. The condition is FALSE only with explicit evidence that blocking is
  impossible (none seen); otherwise UNKNOWN ⇒ default (RETAIN with restore blocked).

### Other facts carried from DATA_NOTES / GOLD_TRACE

- Sample gold cites only `file_id`s; the contract also allows activity_id/audit_id (kept as a fallback, §Q2).
- INCOMPLETE gold verifies every obligation (40 VERIFY_RECORD_ABSENT vs 21 DELETE_RECORD; 17
  VERIFY_RECORD_PRESENT for audit records); backups verify as VERIFY_RESTORE_BLOCKED.
- Physical replicas report under the logical system; present in any copy ⇒ PRESENT.
- Samples have 0 NOT_APPLICABLE; CLASSIFY_REQUEST (10 rows, all "non-deletion") is a cross-check.
- `email_hash` = sha256(raw email), 850/850.

## 6. Decision log

| Date | Decision | Why |
|---|---|---|
| 2026-10-25 | Evidence eligibility = manifest `captured_at ≤ audit_at` (file level) | Q2: gold never cites later files even when they contain earlier-timestamped lines |
| 2026-10-25 | ABSENT may be proven by a full-table snapshot omitting the resource | Q2: 4/75 gold citations; refines HANDOFF "never infer ABSENT from not mentioning" (representation corrected in 0b) |
| 2026-10-25 | Log record = trace_id group | Q3: lookup key and resource_id are on different lines |
| 2026-10-25 | Category from record_type → container name → log event name → Jev fallback | Q1 |
| 2026-10-25 | Accept 8/111 unreachable resources rather than use post-audit evidence | AGENTS.md §6.2 / CLAUDE.md hard rule |
| 2026-10-25 | ~~Account resolution via global request↔workflow-activity assignment~~ (superseded in 0b) | Q3c: identifiers resolve only 15/32 (number later found to leak future evidence) |
| 2026-10-25 | ~~Only default rule branches implemented~~ (superseded in 0b) | Q5: no condition failures in data |
| 2026-10-25 | Phase-0 scripts live in `code/tools/p0_*.py`; recon/trace scripts moved to `code/` | HANDOFF Phase 0 step 6 |
| 2026-10-25 | **0b** Measurements cutoff-safe on files, activity and audit rows; exact identifier matching *(partly superseded by 0c)* | Codex review finding 1: account baseline leaked future evidence (15→12/32); substring `hit()` |
| 2026-10-25 | **0b** Subject-level account linking: reference links first, workflow timing only ranks; default = nearest to reported_at, flagged *(partly superseded by 0c)* | Codex finding 2: repeated requests (case_33/case_52); 0b measurement 12/32 ref links, default 8/20 |
| 2026-10-25 | **0b** `SnapshotCoverage` contract separate from `Observation`; cite the latest file that establishes the state (post-deletion, most physical copies, latest) *(partly superseded by 0c)* | Codex finding 3: empty collection in evidence_51; case_04 cites evidence_54 not evidence_90 |
| 2026-10-25 | **0b** Completion blockers with exact output (§3.5); never COMPLETE silently | Codex finding 4 |
| 2026-10-25 | **0b** Activity/audit citations allowed as a flagged fallback; policy conditions tri-state | Codex finding 5; participant contract allows these citations |
| 2026-10-25 | **0b** 8 "unreachable" resources measured without PNGs; spec 0009 checks evidence_37 / evidence_42 | Codex verification note |
| 2026-10-25 | **0b** Samples are a regression set; synthetic + metamorphic cases are the held-out evidence; scorer tables added to 0005 and 0008 *(partly superseded by 0c)* | Codex evaluation corrections |
| 2026-10-25 | **0c** Identity is strict: post-cutoff audit rows never read | Second review: 0b reverted later changes using post-cutoff rows; `p0_q6_identity_cutoff.py`: 0/550 requests have post-cutoff identity rows or snapshot updates, so strict = revert on this data |
| 2026-10-25 | **0c** Absence rule = superseded-filter, then latest with replica coverage, else latest; executable assertion; labelled post hoc | Second review: 0b "most copies" rule reproduces 3/4 (case_04 → evidence_29) |
| 2026-10-25 | **0c** Ranked (ungrounded) accounts never support COMPLETE (`ACCOUNT_UNGROUNDED` blocker); linkage accuracy reported separately | Second review: default wrong on 12/20; caps sample status at 23/32 until linking improves |
| 2026-10-25 | **0c** Only state-check activity (CHECK_DATA_FLOW / CHECK_RESTORE_ACCESS) can establish state; operational claims never | Second review: 0010 vs 0012 contradiction |
| 2026-10-25 | **0c** Validator: `[]` ⇔ NOT_APPLICABLE, except INCOMPLETE `[]` with a blocker flag | Second review: 0004 vs 0012 contradiction |
| 2026-10-25 | **0c** FALSE policy condition ⇒ `POLICY_UNDEFINED` blocker, no inferred inverse action | Second review: rules do not define inverse branches |
| 2026-10-25 | **0c** Synthetic + metamorphic cases are custom validation, not a holdout | Second review |
| 2026-10-25 | **0d** Absence rule has no fallback to superseded snapshots: no surviving candidate ⇒ UNKNOWN_STATE | Third review: `or cs` fallback selected a stale snapshot; counterexample asserted |
| 2026-10-25 | **0d** Multi-grounded: current = most recent grounded link; older grounded accounts remain historical obligations unless evidence excludes them; measurement uses link times | Third review: newer link does not invalidate an older grounded account; script used workflow timing |
| 2026-10-25 | **0d** Post-cutoff identity snapshot values excluded, not just flagged | Third review: flagging is not exclusion (0/550 affected) |
| 2026-10-25 | **0d** `Observation.source_kind` includes `"activity"`; `file_id` → `evidence_id` | Third review: schema mismatch with spec 0010 |
| 2026-10-25 | **Phase 0 closed.** Grounded accounts are the default; ranked accounts only in the 0015 ablation, labelled as guesses. 23/32 is a conditional upper bound on sample status under current linking, not a measured accuracy or dataset ceiling. Next focus: grounded discovery, not re-fitting inspected samples | Third review sign-off |
| 2026-10-25 | [overnight] Evidence parsing: inventory coverage only for systems in `snapshot_scope`; generic-store coverage for every known collection even with 0 rows; free-text names are never identifiers | spec 0007; matches `p0_q2b_coverage.py` account coverage |
| 2026-10-25 | [overnight] PNG rows take the screen's category only when the resource prefix belongs to the screen's system; vision emails outside the identity universe are dropped | spec 0009: evidence_04 shows a support_ id on the account console; decoy company emails on evidence_32 |
| 2026-10-25 | [overnight] Absence by omission must cover the copy where the resource was last seen when that was a replica snapshot; trace records ignore infrastructure lines (`cache_lookup`, `connection_acquired`, `dependency_*`); `*_completed` read events count as presence | spec 0010: case_05 replica drift, case_15 cache miss read as absence, case_03/18 readbacks; state_report 104/111 states, 75/75 proofs |
| 2026-10-25 | [overnight] Grounded linkage stays 12/32 on samples (167/518 overall): the 20 ungrounded sample accounts and 7 anonymized analytics records have no eligible grounded link; recall target 85% not attainable under grounding | spec 0010 inspection; contract over score |
| 2026-10-25 | [overnight] No separate `cite.py`: the obligation proof from `timeline.state_at` (observed → omission → state-check activity) is the citation; generic snapshots cover only collections present in the same file | spec 0012: one rule, one implementation; tombstone_17 omission came from a collection the snapshot never held |
