# Spec 0012 — planner-and-evidence: design

Contracts: `code/docs/TECHNICAL_DESIGN.md` §3. Data facts: §5.

- `ghostaudit/planner.py`: `plan(obligations, status) -> list[Step]` using the template table; then
  `serialize.canonical`.
- `ghostaudit/cite.py`: `cite(obligation, audit_at, ledger, coverage, activity) -> Citation(id, kind, rule)`.
- Measure on samples: blockers per status (phase-0b baseline: 0 UNRESOLVED_ACCOUNT; ACCOUNT_LINK_DEFAULT on 9
  COMPLETE (2 right account) and 11 INCOMPLETE (6 right) cases).
- `ghostaudit/pipeline.py`: `run_case(request, ctx) -> (status, steps, diagnostics)`; main.py iterates cases.
- Diagnostics JSONL in `runs/` per case: discovered resources with provenance, states, obligations.
