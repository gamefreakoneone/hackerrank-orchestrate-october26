# post_audit_evidence_ignored

A snapshot captured **after** audit_at contains a search document for the subject whose own timestamp is before audit_at. Eligibility is by the file's captured_at, so it must be ignored; the eligible readback proves the account absent and the case is COMPLETE citing only the eligible file.

Expected output (`expected.csv`) and flags (`expected_flags.json`) were written from the rules in AGENTS.md §6 and TECHNICAL_DESIGN §3–5 before the pipeline was run on this case. All people, emails and identifiers are fictional (`example.net`).
