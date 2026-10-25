# tombstone_active_sync

The account is gone (readback 404) but its tombstone still holds the name and email (policy: keep only user_id ⇒ REDACT) and a connector keyed on the email is still enabled (active data flow ⇒ disable first).

Expected output (`expected.csv`) and flags (`expected_flags.json`) were written from the rules in AGENTS.md §6 and TECHNICAL_DESIGN §3–5 before the pipeline was run on this case. All people, emails and identifiers are fictional (`example.net`).
