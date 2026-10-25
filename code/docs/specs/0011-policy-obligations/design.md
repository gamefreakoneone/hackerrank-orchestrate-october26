# Spec 0011 — policy-obligations: design

Contracts: `code/docs/TECHNICAL_DESIGN.md` §3. Data facts: §5.

- `ghostaudit/policy.py`: `category_of(obs) -> str`; `required_state(category) -> RequiredState` from
  `deletion_rules.csv` actions: DELETE→ABSENT, REDACT→REDACTED, ANONYMIZE→ANONYMIZED, RETAIN→PRESENT
  (BACKUP_ARCHIVE→BLOCKED).
- `ghostaudit/obligations.py`: `build(case_resources, states) -> list[Obligation]`; `satisfied` comparison table.
- Account: always one USER_PROFILE obligation for the resolved account.
- Examples from gold: support message → REDACT (case_11 support_864), ticket attachment PDF → DELETE (case_07
  support_001), analytics contact lookup with `email_opt_in` → DELETE (case_12), tombstone with PII → REDACT (case_32).
