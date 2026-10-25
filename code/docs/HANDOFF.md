# HANDOFF — Ghost Data Still Exists (deletion-audit agent)

Place at `code/docs/HANDOFF.md`. Read this fully once. It is the design brief from the planning
phase; decisions here are binding unless the data proves them wrong (then record why in
`TECHNICAL_DESIGN.md` → "Decision log").

---

## 1. What we are building

A terminal-runnable Python system that reads `dataset/` and writes root `output.csv`
(`case_id,deletion_status,steps_json`, exactly 518 rows) for `dataset/deletion_requests.csv`,
following `problem_statement.md` and `AGENTS.md` §6 exactly.

Scoring: output CSV 30, code zip 30, AI-judge interview 30, chat transcript (`log.txt`) 10.
So: accuracy first, then clean testable code, then a clear story backed by evaluation numbers.

**Core principle — "code decides, models read."** A deterministic Python engine owns identity
resolution, temporal state at `audit_at`, policy application, completeness decision, step
generation, evidence citation, ordering, and serialization. AI is used only at bounded points:
request intent (multilingual), image evidence extraction, and typed yes/no or choice judgments
that code cannot make reliably. Every AI output is a validated typed fact.

## 2. Facts already established (see `code/docs/DATA_NOTES.md`, `code/docs/GOLD_TRACE.md`)

- 518 requests; 32 samples with gold (10 COMPLETE, 22 INCOMPLETE, **0 NOT_APPLICABLE**).
- `case_id` widths are mixed (`case_33` … `case_550`); input is in numeric order →
  **sort output numerically by the integer suffix**.
- `email_hash` = SHA-256 of the raw email string (850/850). Audit log changes only `email`,
  `phone`, `email_hash`. 100 of 517 request emails match only a historical value.
- **Gold cites only evidence `file_id`s** — never `activity_id` or `audit_id`. `system_activity.csv`
  is for discovery/timelines, not citation.
- Absence is positively observed: COMPLETE verifications cite service-resource exports
  (`profile_lookups.status_code`), readback logs (point-in-time lookups), replica SQL, snapshot bundles.
  Never infer ABSENT from a file merely not mentioning a resource.
- Output `system_id` is the logical service; physical replicas (failover/read/regional/reporting SQL)
  report under the logical system (e.g. failover replica SQL cited for `account_service`).
  Present in any copy ⇒ remaining record.
- Observed resource-type → system_id: account→account_service, search→search_service,
  support→support_platform, analytics→analytics_platform, export→export_service,
  data_flow→integration_service, backup→backup_service, tombstone→identity_service,
  audit_record→security_service. (Derive this mapping from evidence, not a hardcoded table, if possible.)
- Gold obeys the canonical sort (phase → operation order from the problem statement →
  system_id → resource_id) in 32/32 cases. **No dependency-ordering logic needed.**
- Verification covers ALL obligations, not just remediated ones (INCOMPLETE gold: 40
  VERIFY_RECORD_ABSENT vs 21 DELETE_RECORD; 17 VERIFY_RECORD_PRESENT for security audit records).
- Backups: rule says RETAIN, but verification is `VERIFY_RESTORE_BLOCKED`, not `VERIFY_RECORD_PRESENT`.
- Evidence: 94 files — 24 SQL, 28 JSON, 26 logs (≥6 formats), 1 txt, 4 PDF (all have text layers),
  11 PNG (need vision). Activity: 17 event types; `reported_result` ∈ SUCCESS/FAILED/PARTIAL (claims).
- `CHECK_DATA_FLOW` / `CHECK_RESTORE_ACCESS` details state flow/restore status; `LINK_RESOURCE_IDENTITY`
  links a resource to an email + user_id; `RESTORE_BACKUP` names a repopulated downstream resource;
  `CLASSIFY_REQUEST` is the workflow's own intent claim (cross-check only, never decisive).
- Rules: one rule per data category (15). Action templates:
  - DELETE: `REPORT_REMAINING_RECORD` → `DELETE_RECORD` → `VERIFY_RECORD_ABSENT`
  - REDACT (support message, email log, tombstone): `REPORT_EXPOSED_PII` → `REDACT_RECORD` → `VERIFY_RECORD_REDACTED`
  - ANONYMIZE (analytics, telemetry): `REPORT_EXPOSED_PII` → `ANONYMIZE_RECORD` → `VERIFY_RECORD_ANONYMIZED`
  - RETAIN (security audit, legal hold): `VERIFY_RECORD_PRESENT` only
  - BACKUP_ARCHIVE: `REPORT_RESTORE_RISK` → `BLOCK_RESTORE` → `VERIFY_RESTORE_BLOCKED`
  - Active flow (from activity/evidence): `REPORT_ACTIVE_DATA_FLOW` → `DISABLE_DATA_FLOW` → `VERIFY_DATA_FLOW_DISABLED`
  - Tombstone: keep `user_id`; name, email, phone, email_hash must be gone.
- Same resource type can take different actions (analytics sometimes DELETE, support sometimes
  DELETE vs REDACT) → **category comes from evidence (e.g. `record_type`), not system name.**

## 3. Open questions — resolve in Phase 0 from `GOLD_TRACE.md` and short scripts

1. Where each record's `data_category` comes from (`record_type` fields, collection/table names, document type).
2. Evidence-selection rule: when several files mention a resource ≤ `audit_at`, which one does gold cite?
   (Hypothesis: latest observation of that resource at or before `audit_at`, by `captured_at`/`observed_at`.)
3. Discovery recall: do identifier matches + `LINK_RESOURCE_IDENTITY` + fixed-point expansion
   (identifiers → resources → flows/backups/related resources) find every gold resource without decoys?
4. How COMPLETE-case evidence for flows/backups is expressed (gold cites `evidence_92`-style service exports).
5. Whether any condition-failure branch exists in data (shared attachment, expired hold/retention).
   If none appears, implement the default branch only and note it.

Write each answer with supporting numbers into `TECHNICAL_DESIGN.md` → "Data-derived decisions".

## 4. Architecture

```
dataset/*.csv ─► loaders (typed, tz-aware) ─────────────────────────────┐
dataset/evidence ─► parsers (once per file, cached by sha256+version):   │
   sql (sqlite :memory:) · json · logs (generic key=value / JSON-line) ·  │
   txt · pdf (pypdf text) · png (Gemini vision via Strands, typed schema) │
   └─► Observation ledger + inverted index (identifier/resource → obs)    │
per case:                                                                 ▼
  intent gate (Jev choice; keyword cross-check; low confidence → Azure fallback)
     └ not deletion → NOT_APPLICABLE, []
  identity resolver (current + audit history ≤ audit_at, sha256 of every email)
  resource discovery (fixed point)  →  state @ audit_at (latest observation ≤ cutoff;
     claims only fill gaps; any physical copy present ⇒ PRESENT)
  policy → proof obligations (required end state per resource / flow / backup)
  status = all obligations satisfied ? COMPLETE : INCOMPLETE
  planner: findings + remediation (INCOMPLETE) + verification for every obligation
  evidence selection (deterministic rule) → canonical sort → validator → output.csv
  usage ledger → evaluation/usage_report.md
```

### Models and frameworks

| Role | Provider / model | How |
|---|---|---|
| Request intent (choice: DELETION / ACCESS / CORRECTION / EXPORT / OPT_OUT / OTHER) | TypeSafe **Jev** (`JEV_MODEL`) | `typesafe-sdk` directly (not Strands); accept if confidence ≥ `JEV_CONFIDENCE_THRESHOLD` and agrees with keyword check |
| Intent fallback / ambiguity adjudicator | Azure OpenAI `AZURE_DEPLOYMENT_FALLBACK` | Strands `OpenAIModel`, `base_url=AZURE_OPENAI_ENDPOINT` (v1 API), structured output |
| Image evidence extraction (11 PNGs) | Gemini `GEMINI_VISION_MODEL` | Strands `GeminiModel`, structured output; regex-revalidate every extracted identifier |
| Category / condition judgments (only if evidence lacks explicit fields) | Jev choice / yes-no | typed, cached |

Verify current APIs before coding against them: Strands via the `strands` MCP server,
TypeSafe via https://docs.typesafe.ai. Known Strands risks: Gemini structured output has had
bugs — keep a JSON-repair fallback; Azure gpt reasoning deployments may reject `temperature`.

## 5. Repo layout (code.zip = the `code/` directory)

```
AGENTS.md  CLAUDE.md  log.txt  output.csv  .mcp.json      (repo root)
code/
  main.py                      python code/main.py [--cases sample|all] [--out output.csv]
  requirements.txt  README.md  .env.example
  ghostaudit/ loaders.py identity.py evidence/{sql,json,logs,text,pdf,vision,index}.py
              timeline.py policy.py obligations.py planner.py serialize.py validate.py
              intent.py llm/{providers.py,jev.py,hardening.py,cache.py,ledger.py}
  prompts/  config/{models.yaml,pricing.yaml}
  evaluation/ score.py run_eval.py cases/ evaluation_report.md usage_report.md
  tests/
  docs/ HANDOFF.md TECHNICAL_DESIGN.md FEATURE_STATUS.md DATA_NOTES.md GOLD_TRACE.md specs/
  recon.py trace_gold.py
```

## 6. Spec plan

| Spec | Name | Deliverable / exit criteria |
|---|---|---|
| 0001 | scaffold-env-logging | requirements.txt, .env.example, README skeleton, `python code/main.py` stub writing a valid all-NOT_APPLICABLE file; `code/tools/smoke_providers.py` makes one minimal call each to Jev, Azure, Gemini and reports OK/FAIL (no secrets printed) |
| 0002 | dataset-recon | **Completed already** (recon.py, trace_gold.py, DATA_NOTES, GOLD_TRACE). Record evidence + Phase-0 answers |
| 0003 | data-contracts-loaders | Pydantic models for all CSVs + Step schema; Key Contracts in TECHNICAL_DESIGN |
| 0004 | serializer-validator | canonical sort, numeric case sort, compact JSON, hard validator of every AGENTS.md §6.3/6.4/6.6 rule |
| 0005 | scorer-and-split | grader-replica scorer (status acc, step P/R/F1 on (system_id,resource_id,operation), field acc, sequence exact + LCS); frozen 20 dev / 12 holdout split stratified by status; baseline |
| 0006 | identity-resolution | identifier sets as of audit_at incl. historical emails/phones/hashes; tests |
| 0007 | evidence-parsers | sql/json/logs/txt/pdf → Observation ledger with source file_id, timestamp, system, resource, fields, coverage kind; per-file cache |
| 0008 | llm-provider-layer | Strands Azure + Gemini models, Jev client, hardening, cache, usage ledger, env-based routing |
| 0009 | vision-extraction | 11 PNGs → typed observations; identifier regex revalidation; cached |
| 0010 | discovery-and-state | fixed-point resource discovery; state at audit_at; flows/backups/restores |
| 0011 | policy-obligations | rules.csv → obligations; condition checks; tombstone/retention/backup handling |
| 0012 | planner-and-evidence | status, findings/remediation/verification, deterministic evidence selection; sample score target ≥ 90% status |
| 0013 | intent-gate | Jev + keyword + Azure fallback; multilingual; CLASSIFY_REQUEST disagreement report |
| 0014 | custom-eval-and-metamorphic | ≥4 synthetic cases (historical email + decoy, post-audit evidence, non-deletion multilingual, tombstone + active sync, retained backup) + metamorphic tests |
| 0015 | full-run-ablations-reports | cold-cache full run → output.csv; ablations (deterministic-only, no historical ids, trust activity claims); evaluation_report.md; usage_report.md from ledger |
| 0016 | packaging-and-interview | code.zip script (excludes dataset/, .env, caches); README final; `code/docs/INTERVIEW_NOTES.md` with walkthrough case, failures fixed, numbers |

Specs may be split or reordered in Phase 0 if the open-question answers justify it (record why).

## 7. Evaluation requirements (from problem statement)

`code/evaluation/evaluation_report.md` must contain: case-level status accuracy; step- and
field-level accuracy; sequence accuracy; ≥3 team-created cases with rationale; failures found and
improvements made (with commit refs and before/after numbers). Put numbers in Markdown — automated
code review ignores raw .csv/.json/.log. `code/evaluation/usage_report.md`: providers, models,
calls, input/output tokens, total and average tokens per request, estimated cost total and per
request, per model and overall, from the actual final run (cold cache).

---

## PHASE 0 — do this now (no feature code)

1. Follow AGENTS.md §0 logging. Confirm the `tool=`/`model=` values from the runtime.
2. Environment check: `python --version`; install `code/requirements.txt` if present; confirm
   env vars are set (print names only, never values); confirm the `strands` MCP server responds.
   Do one tiny live call per provider only if spec 0001's smoke script exists; otherwise defer.
3. Read `problem_statement.md`, `code/docs/DATA_NOTES.md`, and `code/docs/GOLD_TRACE.md`
   (GOLD_TRACE is long: read the summary table, then grep targeted sections).
4. Answer the §3 open questions with short scripts under `code/tools/` (summarized output only).
5. Create:
   - `code/docs/TECHNICAL_DESIGN.md` — architecture, Key Contracts (Step schema, Observation,
     Obligation, provider interface, CLI), Data-derived decisions, Decision log.
   - `code/docs/FEATURE_STATUS.md` — ledger table of all specs (0002 Completed, others Not started),
     status definitions, update rule.
   - `code/docs/specs/NNNN-name/{requirements,design,tasks,status}.md` for every spec in §6.
     Each `tasks.md` lists exact validation commands. Each `design.md` is concrete enough to
     implement without guessing (functions, data shapes, edge cases from the data).
6. Move `recon.py`/`trace_gold.py` under `code/` if not already there; `.gitignore` for `.env`,
   caches, `runs/`, `__pycache__`, `code.zip`.
7. Commit: `phase 0: technical design, spec plan, data-derived decisions`. Then stop and summarize
   the plan and any decisions that changed from this handoff.

After Phase 0, each later session is: "Implement spec NNNN per CLAUDE.md."
