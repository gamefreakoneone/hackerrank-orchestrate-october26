# Ghost Data Still Exists — deletion-audit agent

Python 3.11+ solution for the HackerRank Orchestrate October 2026 challenge. A deterministic engine
decides every deletion status and step; models only return typed facts (see `docs/TECHNICAL_DESIGN.md`).

## Setup

```bash
pip install -r code/requirements.txt
cp code/.env.example code/.env   # fill in values, or export them in the shell; .env is gitignored
```

## Environment variables

| Variable | Used for |
|---|---|
| `TYPESAFE_API_KEY`, `TYPESAFE_API_BASE`, `JEV_MODEL`, `JEV_CONFIDENCE_THRESHOLD` | TypeSafe Jev (intent, category fallback) |
| `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_DEPLOYMENT_FALLBACK` | Azure OpenAI via Strands (intent adjudication) |
| `GEMINI_API_KEY`, `GEMINI_VISION_MODEL` | Gemini via Strands (PNG evidence extraction) |

## Run

All commands run from the repository root (the folder containing `dataset/`).

```bash
python code/main.py                                  # all 518 requests -> ./output.csv
python code/main.py --cases sample --out runs/sample.csv
```

Flags: `--cases sample|all`, `--out PATH`, `--offline`, `--no-cache`, `--case case_NN ...`.

## Test

```bash
python -m pytest code/tests -q
python code/tools/smoke_providers.py   # one live call per provider; prints OK/FAIL only
```
