# Spec 0012 — planner-and-evidence: design

Contracts: `code/docs/TECHNICAL_DESIGN.md` §3. Data facts: §5.

- `ghostaudit/planner.py`: `plan(obligations, status) -> list[Step]` using the template table; then
  `serialize.canonical`.
- `ghostaudit/cite.py`: `cite(resource_id, system_id, audit_at, ledger) -> str`.
- `ghostaudit/pipeline.py`: `run_case(request, ctx) -> (status, steps, diagnostics)`; main.py iterates cases.
- Diagnostics JSONL in `runs/` per case: discovered resources with provenance, states, obligations.
