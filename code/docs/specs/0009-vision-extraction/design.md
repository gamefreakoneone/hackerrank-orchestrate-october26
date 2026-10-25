# Spec 0009 — vision-extraction: design

Contracts: `code/docs/TECHNICAL_DESIGN.md` §3. Data facts: §5.

- `ghostaudit/evidence/vision.py`: prompt in `code/prompts/vision_extract.md` describing a generic business
  screen (tables, detail panes); no case hints. Map `status_text` with `categories.yaml` status vocab
  (e.g. "Enabled" → enabled=true, "Restore allowed" → restore_allowed=true, "Valid" signature → present).
- Origins: account_admin_portal, search_index_admin, integration_admin, analytics_platform, export_service,
  support_platform, backup_service, security_service, identity_service, object_storage, marketing_platform.
- Manual spot check: security_audit_explorer_20260905.png shows subject `user_03` with audit_record_001..006.
