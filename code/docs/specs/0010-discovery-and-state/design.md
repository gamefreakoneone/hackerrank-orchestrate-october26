# Spec 0010 — discovery-and-state: design

Contracts: `code/docs/TECHNICAL_DESIGN.md` §3. Data facts: §5.

- `ghostaudit/discovery.py`: `discover(subject, request, ledger, activity, assignment) -> dict[resource_id, Evidence]`.
  Fixed point over steps 1–3 with a max of 3 rounds; record provenance (`via="identifier|link|ref|workflow"`).
- `ghostaudit/assignment.py`: `assign_accounts(requests, ledger, activity) -> dict[case_id, account_id]`,
  computed once per run over all requests of the split (sample or all); greedy by ascending distance is
  acceptable if results match Hungarian on samples.
- `ghostaudit/timeline.py`: `state_at(resource_id, audit_at, ledger) -> ResourceState(state, proof_file_id, obs)`.
- Decoy guard: a record linked only by a name or only by `correlation_key` must also share user_id/email/phone/hash.
- Known data facts: deleted accounts show `profile: null, status_code: 404`; anonymized analytics have all
  identifier fields null; replica drift: primary absent but failover/read replica present (case_05).
- Report script `code/tools/discovery_report.py`: per sample case gold-vs-found (reads gold, evaluation only).
