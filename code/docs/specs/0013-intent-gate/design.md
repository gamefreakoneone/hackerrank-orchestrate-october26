# Spec 0013 — intent-gate: design

Contracts: `code/docs/TECHNICAL_DESIGN.md` §3. Data facts: §5.

- `ghostaudit/intent.py`: `classify(text) -> IntentResult(label, confidence, source)`.
- Mixed requests ("delete my account, and also export first") ⇒ DELETION if deletion is requested at all.
- Requests that only ask to verify a past deletion ("Can you verify that my account was deleted?", case_28) are
  DELETION (gold treats them as deletion audits).
- Cache by text hash; ledger rows tagged `task=intent`.
