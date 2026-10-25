# Spec 0009 — vision-extraction: design

Contracts: `code/docs/TECHNICAL_DESIGN.md` §3. Data facts: §5.

- `ghostaudit/evidence/vision.py`: prompt in `code/prompts/vision_extract.md` describing a generic business
  screen (tables, detail panes); no case hints. Map `status_text` with `categories.yaml` status vocab
  (e.g. "Enabled" → enabled=true, "Restore allowed" → restore_allowed=true, "Valid" signature → present).
- Origins: account_admin_portal, search_index_admin, integration_admin, analytics_platform, export_service,
  support_platform, backup_service, security_service, identity_service, object_storage, marketing_platform.
- Manual spot check: security_audit_explorer_20260905.png shows subject `user_03` with audit_record_001..006.
- **Must check (phase 0b):** the 8 sample resources unreachable from pre-cutoff text/CSV were measured with PNG
  contents excluded. Extract and search for them: audit_record_4902/6645/5569/4128/7095/3954/1707 →
  `evidence_37` security_audit_explorer_20260905.png (eligible for all 7 cases; the visible table shows only
  user_03, but check every extracted row); account_004 (case_04, audit 2026-09-07) → `evidence_42`
  deleted_account_reference_20260310.png (eligible); `evidence_04` account_admin_console_20260926.png is captured
  after case_04's cutoff and must not be used. Record found/not-found in status.md and update the ceiling in
  TECHNICAL_DESIGN §5 Q3.
