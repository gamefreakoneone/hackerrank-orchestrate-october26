# Spec 0001 — scaffold-env-logging: requirements

**Depends on:** none

## Goal

Runnable skeleton: dependencies pinned, env template, README skeleton, a `main.py` that writes a valid all-NOT_APPLICABLE `output.csv`, and a provider smoke test.

## Requirements / acceptance criteria

- `code/requirements.txt` pins: pydantic, pypdf, strands-agents (with openai + gemini extras as needed),
  typesafe-sdk, openai, google-genai, PyYAML, pytest (exact versions from the current env: pydantic 2.13.5,
  pypdf 6.17.0, strands-agents 1.62.0, typesafe-sdk 0.7.5, openai 2.54.0, google-genai 2.33.0, PyYAML 6.0.3,
  pytest 9.1.1).
- `code/.env.example` lists every env var from TECHNICAL_DESIGN §3.5 with empty values.
- `code/README.md`: setup, run, env vars, test commands.
- `python code/main.py` writes root `output.csv` with 518 rows `case_id,NOT_APPLICABLE,[]`, numerically sorted.
- `python code/tools/smoke_providers.py` makes one minimal call each to Jev, Azure, Gemini and prints
  `jev: OK|FAIL <error class>` etc. Never prints keys, endpoints or raw responses.
- Root `log.txt` logging is unaffected.

## Out of scope

Anything owned by another spec in `code/docs/FEATURE_STATUS.md`. Hard rules in `CLAUDE.md` apply.
