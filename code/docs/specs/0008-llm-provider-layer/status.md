# Spec 0008 — llm-provider-layer: status

**Status:** Completed (2026-10-25, overnight run)

## Evidence

```text
$ python -m pytest code/tests/test_llm_*.py -q
7 passed, 1 skipped (live test is opt-in)
$ RUN_LIVE=1 python -m pytest code/tests/test_llm_live.py -q
1 passed (azure + gemini structured output, jev noul; all uncached, tokens > 0)
$ python code/tools/smoke_providers.py          # now routed through the shared layer
jev: OK model=jev-1.14.0 tokens=289+24
azure: OK model=gpt-6-luna tokens=189+22
gemini: OK model=gemini-3.8-flash tokens=118+80
$ python code/evaluation/run_eval.py --split dev  # runs/score_20261025T081210Z_dev.md
status 0/20, F1 0.000 — unchanged (layer not used by the pipeline yet)
```

## Scorer snapshot (dev)

| | Status acc | Account linkage | Step F1 | Seq exact |
|---|---|---|---|---|
| before (0007) | 0.000 | not measured | 0.000 | 0.000 |
| after | 0.000 | not measured | 0.000 | 0.000 |

## Notes

- `LLMLayer.call(task, schema, inputs, images, provider)` / `LLMLayer.provider(name)` implement the
  `StructuredCall` contract: cache lookup (key = sha256 of task, provider, configured model, schema JSON, canonical
  inputs, image hashes) → transport → pydantic validation (`hardening.validate`, tolerant `repair_json`) → exactly one
  repair retry carrying the validation error → `LLMError`. Ledger rows: provider, served model, task, tokens, cached,
  latency, attempts.
- `--offline` = cache-only (`LLMUnavailable` on a miss, callers fall back deterministically). `--no-cache` skips cache
  reads only; results are still written so a cold run leaves a reproducible cache.
- Transports: Jev via typesafe-sdk (`inputs = {state, questions: {name: choice|noul}}`, answers returned as typed
  dicts); Azure and Gemini via Strands `Agent(..., structured_output_model=schema)`, a fresh Agent per call; Gemini falls
  back to JSON text + `repair_json` if structured output raises. Params from `code/config/models.yaml`
  (Azure: `reasoning_effort=none`, `temperature=0`; Gemini: `temperature=0` — both accepted live).
- `code/config/pricing.yaml` is intentionally empty: prices for jev-1.14.0, gpt-6-luna and gemini-3.8-flash are not
  established in the repo, so `summarize()` reports cost `None` (never invented). Spec 0015 must source prices or report
  cost as unavailable.
- `tools/smoke_providers.py` now uses the layer (no duplicate Azure/Jev client code).
