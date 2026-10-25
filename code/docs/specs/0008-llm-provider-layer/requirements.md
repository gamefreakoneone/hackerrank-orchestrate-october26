# Spec 0008 — llm-provider-layer: requirements

**Depends on:** 0001

## Goal

Single structured-call layer for Jev, Azure (Strands) and Gemini (Strands) with cache and usage ledger.

## Requirements / acceptance criteria

- Implements `StructuredCall` (TECHNICAL_DESIGN §3.6) for `jev`, `azure`, `gemini`.
- Schema validation + exactly one repair retry (re-ask with validation error) then raise `LLMError`.
- Disk cache `code/.cache/llm/<sha256>.json` (gitignored); `--no-cache` bypass; `--offline` = cache-only.
- Usage ledger appended to `runs/usage_<run_id>.jsonl`; `ledger.summarize()` returns per-model and overall
  calls, input/output tokens, cost (prices from `code/config/pricing.yaml`).
- Model routing from `code/config/models.yaml` + env vars; no secrets in config files or logs.

## Out of scope

Anything owned by another spec in `code/docs/FEATURE_STATUS.md`. Hard rules in `CLAUDE.md` apply.
