# Spec 0010 — discovery-and-state: design

Contracts: `code/docs/TECHNICAL_DESIGN.md` §3. Data facts: §5.

- `ghostaudit/discovery.py`: `discover(subject, request, ledger, activity) -> dict[resource_id, Evidence]`
  (calls `account_link.link_account`; exact identifier matching per spec 0006).
  Fixed point over steps 1–3 with a max of 3 rounds; record provenance (`via="identifier|link|ref|workflow"`).
- `ghostaudit/account_link.py`: `link_account(subject, request, ledger, activity) -> AccountLink(account_id | None,
  via: Literal["ref_link", "ref_link_multi", "workflow_default", "unresolved"], candidates: list[str], flags)`;
  memoized per (user_id, audit_at). Phase-0b baseline (`code/tools/p0_q3c_account_link.py`): ref_link 12/32 correct
  (0 wrong); workflow default 8/20 correct; overall 20/32; 0 unresolved on samples.
- `ghostaudit/timeline.py`: `state_at(resource_id, audit_at, ledger) -> ResourceState(state, proof_file_id, obs)`.
- Decoy guard: a record linked only by a name or only by `correlation_key` must also share user_id/email/phone/hash.
- Known data facts: deleted accounts show `profile: null, status_code: 404`; anonymized analytics have all
  identifier fields null; replica drift: primary absent but failover/read replica present (case_05).
- Report script `code/tools/discovery_report.py`: per sample case gold-vs-found (reads gold, evaluation only).
