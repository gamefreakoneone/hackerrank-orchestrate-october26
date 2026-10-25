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
  2 identity resolver: identifier set as of audit_at (later audit changes reverted)
  3 discovery: exact identifier-linked records (≤ audit_at) → fixed-point expansion
              + subject-level account link (§5 Q3): reference links first, workflow timing only ranks
  4 state @ audit_at per resource: latest establishing observation or SnapshotCoverage (file captured_at ≤ audit_at);
    nothing establishes it ⇒ UNKNOWN
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
    file_id: str                      # evidence_NN (the only citable id)
    captured_at: datetime             # from evidence_files.csv — the cutoff key
    observed_at: datetime | None      # record-level time if present (observed_at, updated_at, log ts)
    source_kind: Literal["sql", "json", "log", "txt", "pdf", "png"]
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
    condition: Literal["TRUE", "FALSE", "UNKNOWN"]  # rule condition at audit_at; UNKNOWN ⇒ default branch, flagged
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
| `UNRESOLVED_ACCOUNT` | no reference link and no unowned workflow candidate | INCOMPLETE | no account steps (no resource_id to name); other obligations planned normally |
| `ACCOUNT_LINK_DEFAULT` | account chosen by the workflow-timing default (§5 Q3) | not a blocker | planned normally (COMPLETE still needs proof of the account's state) |
| `UNKNOWN_STATE` | no eligible file / coverage / activity establishes the state | INCOMPLETE | no finding, no remediation for it; VERIFICATION step (required end state) with `""` |
| `EMPTY_OBLIGATIONS` | deletion authorized but nothing discovered | INCOMPLETE | `[]` |
| `CONDITION_DEFAULTED` | rule condition has no field (UNKNOWN) | not a blocker | default branch |
| `ACTIVITY_CITATION` | proof is an activity_id / audit_id | not a blocker | cited as is |

No finding or evidence is ever invented to fill a blocker. The validator downgrades "INCOMPLETE without
findings" from error to warning only when a blocker flag is present.

Phase-0b measurement on samples (`p0_q3c_account_link.py` §C, gold as oracle): 0 `UNRESOLVED_ACCOUNT`;
`ACCOUNT_LINK_DEFAULT` on 20/32 cases (9 COMPLETE: 2 right account; 11 INCOMPLETE: 6 right). Treating the
default as a blocker would turn 9/10 COMPLETE samples INCOMPLETE, so it is a flag, not a blocker.
`UNKNOWN_STATE` over gold resources: 8/111 (all retained audit records in INCOMPLETE cases, plus account_004 in
COMPLETE case_04, which is a linking miss rather than a state gap since evidence_54 covers it).

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
measurement cutoff-safe (files by manifest captured_at, activity and audit rows by event_time, all ≤ audit_at;
identity values as of audit_at) and replaced substring matching with exact identifier matching.

**Evaluation honesty.** Every sample answer was inspected to make these decisions, so the 32 samples (and any
dev/holdout split of them) are a **regression set**, not untouched validation. Held-out evidence comes from
synthetic cases and metamorphic tests (spec 0014). All rules below are fitted to samples; small counts (e.g.
4/4) are hypotheses that the full run must keep checking via diagnostics.

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
  2. absence by omission: eligible `SnapshotCoverage` of the system, captured **after the resource's last
     DELETE_RECORD activity** (if any), not containing the resource; prefer the snapshot covering **more physical
     copies**, then the latest.
  - case_04 (audit 09-07, no deletion activity): `evidence_54` (09-02, primary **and** failover replica) beats the
    newer `evidence_90` (09-05, inventory scoped to account_service, primary `customer_profiles` only, 0 rows).
    A primary-only snapshot cannot establish absence across replicas — case_05 shows exactly this drift (primary
    empty, failover replica still holds account_005). Same choice for case_01/02 (evidence_10 is older and also
    two copies).
  - case_31 (audit 09-15, account_4857 deleted 09-06): `evidence_54` and `evidence_90` predate the deletion, so they
    cannot prove it; of `evidence_07` (09-13) and `evidence_51` (09-15) the latest is cited.
  3. fallback when no file establishes the state: an `activity_id`/`audit_id` ≤ audit_at whose content states the
     result (the participant contract allows these citations; samples never needed them), flagged
     `ACTIVITY_CITATION`.
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
  - B. Subject-level linking, reference links first (pre-deletion rows, customer/subject_reference, LINK activity,
    trace groups, all ≤ audit_at): **12/32 resolved, 0 wrong**. For the other 20, workflow candidates not linked
    to another user, ranked; defaults measured on those 20: nearest to reported_at **8**, latest before reported_at
    5, earliest after request 2, unique-candidate-only 2 (18 none), claim-aware nearest (prefer activities this
    request is the closest request to) 8. **Default = nearest to reported_at, flagged `ACCOUNT_LINK_DEFAULT`.**
    Overall account correct 20/32; 0 unresolved.
  - No one-to-one constraint: unique account ownership does not imply unique request ownership. The evaluation
    set has **1 subject with 2 requests (case_33, case_52)**; linking is per subject, with per-request cutoffs.
  - Tombstones carry `subject_reference` (user_id) but no account id: they confirm the subject, not the account.
- **Ceiling under the cutoff rule (text + CSV only):** of 111 gold resources, 89 appear in a pre-audit text file,
  14 only in pre-audit activity, **8 in neither**: account_004 (case_04) and audit_record_4902/6645/5569/4128/
  7095/3954/1707. PNG contents were **excluded** from this count, so it is not a proven ceiling. Spec 0009 must
  check `evidence_37` security_audit_explorer_20260905.png (eligible for all 7 audit-record cases; the visible
  table shows only user_03's audit_record_001–006) and `evidence_42` deleted_account_reference_20260310.png for
  account_004 (`evidence_04` account_admin_console_20260926.png is after case_04's cutoff).

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
- ⇒ Conditions are **tri-state** (TRUE / FALSE / UNKNOWN). Where a field exists (retention_until, hold status /
  register entry, restore_allowed) it is evaluated at audit_at and a FALSE result switches the branch (e.g.
  expired retention ⇒ DELETE). Where no field exists ⇒ UNKNOWN ⇒ default branch, flagged `CONDITION_DEFAULTED`.
  Not observing a FALSE in samples is not a reason to ignore it; synthetic cases (0014) cover the FALSE branches.

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
| 2026-10-25 | **0b** Measurements cutoff-safe on files, activity and audit rows; exact identifier matching | Codex review finding 1: account baseline leaked future evidence (15→12/32); substring `hit()` |
| 2026-10-25 | **0b** Subject-level account linking: reference links first, workflow timing only ranks; default = nearest to reported_at, flagged | Codex finding 2: repeated requests (case_33/case_52); 0b measurement 12/32 ref links, default 8/20 |
| 2026-10-25 | **0b** `SnapshotCoverage` contract separate from `Observation`; cite the latest file that establishes the state (post-deletion, most physical copies, latest) | Codex finding 3: empty collection in evidence_51; case_04 cites evidence_54 not evidence_90 |
| 2026-10-25 | **0b** Completion blockers with exact output (§3.5); never COMPLETE silently | Codex finding 4 |
| 2026-10-25 | **0b** Activity/audit citations allowed as a flagged fallback; policy conditions tri-state | Codex finding 5; participant contract allows these citations |
| 2026-10-25 | **0b** 8 "unreachable" resources measured without PNGs; spec 0009 checks evidence_37 / evidence_42 | Codex verification note |
| 2026-10-25 | **0b** Samples are a regression set; synthetic + metamorphic cases are the held-out evidence; scorer tables added to 0005 and 0008 | Codex evaluation corrections |
