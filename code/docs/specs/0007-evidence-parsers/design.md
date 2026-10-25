# Spec 0007 — evidence-parsers: design

Contracts: `code/docs/TECHNICAL_DESIGN.md` §3. Data facts: §5.

- `ghostaudit/evidence/sql.py`: `sqlite3.connect(":memory:").executescript(text)`; iterate tables; columns
  `record_json` parsed as JSON and merged into fields; `physical_copy` = table suffix (`_primary`,
  `_failover_replica`, `_read_replica`, `_replica_eu_west`, …; bare `customer_profiles` = primary). Coverage: one
  `SnapshotCoverage` per (table[, collection_name]) — generic `customer_data_*` tables give one coverage per
  collection_name present **and** per collection listed in `snapshot_scope`/known for that origin even if 0 rows;
  inventory files use `snapshot_scope(origin_system, captured_at)` as the scope (e.g. `evidence_90` scope =
  account_service only).
- `ghostaudit/evidence/json_.py`: walk; any dict with a `resource_id` string is a record; inherit
  `collection`/`data_store`/`captured_at`/`observed_at` from ancestors; `service_resource_export` keys
  `service_exports.<system_id>.<collection>` give system_id directly. Snapshot bundles: each
  `snapshots[]` entry is a `SnapshotCoverage` (data_store, collection, captured_at), even when `records` is empty.
  `service_resource_export` lookups are per-resource observations, **not** full coverage.
- `ghostaudit/evidence/logs.py`: format detectors (key=value, JSON-line, syslog `<15>1`, bracketed `[LEVEL]`,
  pipe-separated, cloud `requestId= message="..."`); normalize each line to `{ts, service, trace_id, kv}`;
  group by trace_id; record fields include `lookup_key`, `subject_key`, `subject_ref`, `correlation_key`,
  `matched_value`, `status`/`http_status`, `enabled`, `eligible`, `deletion_block`, `retention_until`, `event`.
- `ghostaudit/evidence/text.py`: txt handover table rows `- ts | system | resource | RECORD_TYPE | STATE | identifier`.
- `ghostaudit/evidence/pdf.py`: pypdf text; resource ids via RES_RE; identifiers via regex; category by document
  title (`DELIVERY ADDRESS CORRECTION REQUEST` attachment → SUPPORT_ATTACHMENT; `DISPUTED ORDERS AND TAX RECORDS
  REGISTER` → LEGAL_HOLD_RECORD; `COMPLIANCE JOURNAL` → SECURITY_AUDIT_LOG; `CUSTOMER STATEMENT` → by content).
- `ghostaudit/evidence/index.py`: builds ledger; `eligible(obs, audit_at)` = `obs.captured_at <= audit_at`.
- Category/event maps live in `code/config/categories.yaml` (data, not code).
