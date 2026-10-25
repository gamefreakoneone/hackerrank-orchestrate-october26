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

Flags: `--cases sample|all`, `--out PATH`, `--offline` (cache-only model calls; keyword intent marked provisional),
`--no-cache` (skip cache reads: cold run), `--case case_NN ...` (subset, skips the full-file validator),
`--data-root DIR` (alternative dataset directory, used by the custom evaluation overlays).

Each run also writes `<out>.diagnostics.jsonl` (per-case flags, account link, obligations), a usage ledger
`runs/usage_<run_id>.jsonl` and a manifest `runs/<run_id>.manifest.json` (git revision, output checksum).

## Evaluate

```bash
python code/evaluation/run_eval.py --split dev        # samples: run + score (regression set, not a holdout)
python code/evaluation/score.py runs/sample.csv dataset/sample_output.csv --split all
python code/evaluation/run_custom.py                  # synthetic custom cases (overlay on a temp dataset copy)
python code/tools/discovery_report.py --split all     # discovery + account linkage vs samples
python code/tools/state_report.py                     # reconstructed state/proof vs samples
python code/tools/intent_report.py runs/all.diagnostics.jsonl
python -c "import sys;sys.path.insert(0,'code');from ghostaudit.validate import cli;cli()"   # validate ./output.csv
```

## Test

```bash
python -m pytest code/tests -q                      # offline; RUN_LIVE=1 enables the live-model tests
python code/tools/smoke_providers.py   # one live call per provider; prints OK/FAIL only
```
