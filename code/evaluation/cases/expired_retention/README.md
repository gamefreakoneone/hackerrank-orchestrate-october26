# expired_retention

The audit record's retention_until is before audit_at, so the RETAIN rule's condition is FALSE. The rules define no action for that branch: no inferred DELETE, no step for the record, POLICY_UNDEFINED blocker ⇒ INCOMPLETE.

Expected output (`expected.csv`) and flags (`expected_flags.json`) were written from the rules in AGENTS.md §6 and TECHNICAL_DESIGN §3–5 before the pipeline was run on this case. All people, emails and identifiers are fictional (`example.net`).
