# repeated_request

One subject files two requests. At the first audit_at the only readback shows the account present (INCOMPLETE); a later readback shows it gone before the second audit_at (COMPLETE). Each request uses only evidence up to its own cutoff; the account link is shared.

Expected output (`expected.csv`) and flags (`expected_flags.json`) were written from the rules in AGENTS.md §6 and TECHNICAL_DESIGN §3–5 before the pipeline was run on this case. All people, emails and identifiers are fictional (`example.net`).
