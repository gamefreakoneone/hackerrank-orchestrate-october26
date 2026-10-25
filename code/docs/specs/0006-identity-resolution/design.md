# Spec 0006 — identity-resolution: design

Contracts: `code/docs/TECHNICAL_DESIGN.md` §3. Data facts: §5.

- `ghostaudit/identity.py`: indexes `email -> user_id` over current snapshot and every audit old/new email.
  Collect old and new values from the subject's audit rows with event_time ≤ audit_at; add current snapshot values
  only when `snapshot.updated_at ≤ audit_at`. Email→user index is built per cutoff from the same eligible values.
- Tests: appending a synthetic post-cutoff audit row for the subject must not change `resolve()` for that request;
  setting the snapshot's updated_at after audit_at removes its values from the identifier set.
- `Subject.matches(value: str) -> bool` uses exact equality per type (emails/hashes case-insensitive, phones
  digits-only normalized, names exact Unicode NFC equality — **never substring**: decoys `Jonas Berglund`,
  `Mateo Rios Gil`).
- `Subject.key_values()` used by the evidence index.
