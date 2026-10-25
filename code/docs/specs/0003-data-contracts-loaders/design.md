# Spec 0003 — data-contracts-loaders: design

Contracts: `code/docs/TECHNICAL_DESIGN.md` §3. Data facts: §5.

- `ghostaudit/models.py`: enums `Phase`, `Operation`, `State`, `Status`; dicts `OP_PHASE`, `OP_STATE`,
  `OP_ORDER` (TECHNICAL_DESIGN §3.1); models with `model_config = ConfigDict(frozen=True)`.
- `ghostaudit/loaders.py`: `parse_ts(s) -> datetime` (accepts `Z`); `read_csv(path) -> list[dict]`
  (`utf-8-sig`, `newline=""`); `Dataset` dataclass: `requests`, `identities: dict[user_id, Identity]`,
  `audit: list[AuditEvent]` sorted by (event_time, audit_id), `activity` sorted by (event_time, activity_id),
  `rules: dict[data_category, Rule]`, `evidence: dict[file_id, EvidenceFile]` (absolute path resolved,
  existence asserted).
- `case_key(case_id) -> int`.
- Edge cases: empty `old_value` in audit log; `details` with commas (csv module handles quotes);
  request_text with non-ASCII; mixed case_id widths.
