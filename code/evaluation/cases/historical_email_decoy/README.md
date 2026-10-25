# historical_email_decoy

The request uses the subject's **historical** email (changed before audit_at). A readback grounds account_9001 (404) and a search document still holds the old email. Two decoys share or extend the name ('Elin Strand' with another email, 'Elin Strandberg'); a name alone never links, so they must not appear.

Expected output (`expected.csv`) and flags (`expected_flags.json`) were written from the rules in AGENTS.md §6 and TECHNICAL_DESIGN §3–5 before the pipeline was run on this case. All people, emails and identifiers are fictional (`example.net`).
