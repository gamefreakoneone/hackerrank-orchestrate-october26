# Spec 0007 — evidence-parsers: status

**Status:** Completed (2026-10-25, overnight run)

## Evidence

```text
$ python -m pytest code/tests/test_evidence_*.py -q
18 passed
$ python code/tools/evidence_coverage.py
total observations 3012 {activity: 117, json: 890, log: 1071, pdf: 2, sql: 891, txt: 41}; coverage rows 472;
files without records 13 (11 PNG → spec 0009; evidence_18 customer statement and evidence_27 legal register
name no resource_id)
$ python code/evaluation/run_eval.py --split dev      # runs/score_20261025T080911Z_dev.md
status 0/20, F1 0.000 (parsers not wired into the stub pipeline yet)
Parser sanity (samples, exact identifier lookup through the index, eligible files only): 76/111 gold resources
reached, 1 extra — Phase-0b reference 77/111 (that figure also used LINK_RESOURCE_IDENTITY activity, spec 0010).
0 log lines unparsed; 0 trace groups with more than one resource_id; every observation has system_id and category.
```

## Scorer snapshot (dev)

| | Status acc | Account linkage | Step F1 | Seq exact |
|---|---|---|---|---|
| before (0006) | 0.000 | not measured | 0.000 | 0.000 |
| after | 0.000 | not measured | 0.000 | 0.000 |

## Notes

- Modules: `evidence/{derive,sql,json_,logs,text,pdf,index}.py`; maps in `code/config/categories.yaml`.
- Identifiers are stored normalized (emails/hashes lower-case, phone digits, NFC names, user ids) so
  `Subject.key_values()` looks them up directly. Phones come from `*phone*` fields or `+`-prefixed tokens; names only
  from name fields (free-text names are never identifiers; a name alone never links — spec 0010 decoy guard).
- SQL: generic `customer_data_*` tables merge `record_json`; coverage per (table, known collection) even with 0 rows
  (matches `p0_q2b_coverage.py`'s account coverage). Inventory tables emit coverage only for systems listed in
  `snapshot_scope` (evidence_90 → account_service only). Physical copy = table suffix; bare tables are `primary`.
- JSON: outermost dict with a `resource_id` is a record; `service_exports.<system>.<collection>` sets system_id;
  bundle `snapshots[]` → coverage with `physical_copy="bundle"` (even when empty, evidence_51). Single-collection
  captures (evidence_56/59) and service-export lookups are observations only, not coverage.
- Logs: one parser per line (JSON, syslog, bracketed, pipe, cloud `message=`, key=value); trace ids are `tr-*`/`rb-*`
  (positional instance names such as `collector-3` are not traces); one observation per resource per group with the
  union of all lines' identifiers. Added `retained_order_*` → LEGAL_HOLD_RECORD and `thumbnail_failed` →
  SUPPORT_ATTACHMENT; `contact_lookup_completed` → MARKETING_PROFILE and `contact_query_*` (legacy contact index) →
  SECONDARY_IDENTIFIER (both DELETE, matching TECHNICAL_DESIGN §5 Q1's gold notes).
- State-check activity (`CHECK_DATA_FLOW`, `CHECK_RESTORE_ACCESS`, SUCCESS) → `source_kind="activity"` observations
  (`enabled=true` / `restore_allowed=true` parsed from the details text).
- Cache: `code/.cache/evidence/<sha256(bytes|PARSER_VERSION|file_id|captured_at)>.json`. Parsing all files takes
  ~0.3 s, so the cache is a formality.
