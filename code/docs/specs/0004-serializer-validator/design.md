# Spec 0004 — serializer-validator: design

Contracts: `code/docs/TECHNICAL_DESIGN.md` §3. Data facts: §5.

- `ghostaudit/serialize.py`: `canonical(steps: list[Step]) -> list[Step]` sorts by
  `(OP_ORDER[op], system_id, resource_id)` and reassigns `step_no`; `dumps_steps(steps) -> str`.
- `ghostaudit/validate.py`: pure functions, each rule a small checker returning messages prefixed with case_id.
- Test fixtures: `sample_output.csv` must validate clean (it is the oracle for format); mutated copies
  (swap order, wrong state, cite late file) must fail with the expected message.
