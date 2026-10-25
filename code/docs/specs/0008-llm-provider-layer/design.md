# Spec 0008 — llm-provider-layer: design

Contracts: `code/docs/TECHNICAL_DESIGN.md` §3. Data facts: §5.

- `ghostaudit/llm/providers.py`: `make_provider(name) -> StructuredCall`.
  Strands Agent with `structured_output_model=schema` for azure/gemini (confirm current API via the strands MCP
  `search_docs("structured output")`); Gemini: if structured output fails, fall back to JSON text + `hardening.repair_json`.
  Azure: omit `temperature` if the deployment is a reasoning model (config flag).
- `ghostaudit/llm/jev.py`: typesafe-sdk choice/yes-no question wrapper returning `(answer, confidence, usage)`.
  Follow the `typesafe:typesafe-ai` skill for question phrasing.
- `ghostaudit/llm/hardening.py`: `repair_json(text)`, `validate(schema, data)`.
- `ghostaudit/llm/cache.py`, `ghostaudit/llm/ledger.py` as specified.
- Tests use a fake provider; one opt-in live test behind `RUN_LIVE=1`.
- Live provider access is **not yet verified** (Phase 0 only checked env var names); this spec's smoke run is the
  first proof. The scorer snapshot should be unchanged (no pipeline use yet) — record it to prove no regression.
