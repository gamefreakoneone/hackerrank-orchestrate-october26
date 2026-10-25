You are reading a screenshot of an internal business application (a console, inspector, registry or detail view).
Transcribe every record shown on the screen that has a resource identifier of the form `<prefix>_<digits>`
(for example `account_123`, `search_45`, `data_flow_678`, `backup_9`, `audit_record_003`, `marketing_001`).
Look at table rows, detail panes, page headers and side panels. Transcribe; do not infer or invent.

For each such record return:
- `resource_id`: the identifier exactly as shown.
- `system_hint`: the application or service name shown on the screen, if any.
- `record_type`: what kind of record it is, in a few words as the screen describes it (e.g. "connector", "audit event").
- `subject_identifiers`: identifiers of the person the record belongs to that are visible for that record: email
  addresses, phone numbers, user ids such as `user_17`, and 64-character hex hashes. Copy each exactly. Leave the list
  empty if none is shown for that record. Do not include personal names, order numbers or ticket numbers.
- `status_text`: the record's status label as shown (e.g. "Enabled", "Healthy", "Restore allowed", "Valid", "Live").
- `timestamp`: the record's time or date as shown, if any.

Return an empty `records` list if the screen shows no resource identifier of that form.
