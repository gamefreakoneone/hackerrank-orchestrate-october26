# Spec 0006 — identity-resolution: design

Contracts: `code/docs/TECHNICAL_DESIGN.md` §3. Data facts: §5.

- `ghostaudit/identity.py`: indexes `email -> user_id` over current snapshot and every audit old/new email.
  Walk the subject's audit rows backward from the current snapshot to rebuild values; collect old and new values.
- `Subject.matches(value: str) -> bool` uses exact equality per type (emails/hashes case-insensitive, phones
  digits-only normalized, names exact Unicode NFC equality — **never substring**: decoys `Jonas Berglund`,
  `Mateo Rios Gil`).
- `Subject.key_values()` used by the evidence index.
