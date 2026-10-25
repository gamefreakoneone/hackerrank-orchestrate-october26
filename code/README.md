# Ghost Data Still Exists — deletion-audit agent

Python 3.11+ solution for the HackerRank Orchestrate October 2026 challenge. A deterministic engine
decides every deletion status and step; models only return typed facts (see `docs/TECHNICAL_DESIGN.md`,
`docs/INTERVIEW_NOTES.md`).

## Layout

The repository root holds `dataset/` (not shipped) and this `code/` folder; `code.zip` contains the contents of
`code/`. To run from the zip, unzip it into a folder named `code/` placed next to `dataset/`.

## Architecture

| Stage | Module | Decides / produces |
|---|---|---|
| Intent gate | `ghostaudit/intent.py` | Jev choice + keyword cross-check, Azure adjudication; non-deletion ⇒ NOT_APPLICABLE |
| Identity | `ghostaudit/identity.py` | subject identifiers valid at `audit_at` (current + historical, hashes) |
| Evidence | `ghostaudit/evidence/` | observations + snapshot coverage from SQL/JSON/logs/txt/PDF, PNG via Gemini |
| Discovery | `ghostaudit/discovery.py`, `account_link.py` | exact-identifier links, grounded account (ranked guesses only in diagnostics) |
| State | `ghostaudit/timeline.py` | state at `audit_at` + the evidence that establishes it |
| Policy | `ghostaudit/policy.py`, `obligations.py` | required end state, tri-state rule conditions, satisfied? |
| Plan | `ghostaudit/planner.py`, `serialize.py`, `validate.py` | status, findings/remediation/verification, canonical JSON, hard validator |
| Models | `ghostaudit/llm/` | one structured-call layer: cache, validation, one repair retry, usage ledger |

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
python code/main.py --cases sample --offline --no-cache --out runs/sample_offline.csv   # deterministic, no model calls
```

Selected-output contract (spec 0025): only the release configuration may write the repository-root `output.csv`
(any path resolving to it, e.g. `./output.csv` or `code/../output.csv`): `--cases all`, no `--case`, no `--ablate`,
`--ungrounded-account-steps none`, not `--offline`, and `--data-root` resolving to `dataset/` (`--no-cache` is
allowed). Anything else stops before loading data or calling a provider, e.g.
`refusing to replace the selected .../output.csv: not the release configuration (--cases sample; --offline); pass
--out to another path`. All those modes work with `--out` elsewhere (a scratch file named `output.csv` is fine).

Flags: `--cases sample|all`, `--out PATH`, `--offline` (cache-only model calls; keyword intent marked provisional),
`--no-cache` (skip cache reads: cold run), `--case case_NN ...` (subset, skips the full-file validator),
`--data-root DIR` (alternative dataset directory, used by the custom evaluation overlays).
Evaluation-only ablations (never used for the submitted output): `--ablate no-history`, `--ablate trust-claims`,
`--ungrounded-account-steps ranked`.

Each run also writes `<out>.diagnostics.jsonl` (per-case flags, account link, obligations), a usage ledger
`runs/usage_<run_id>.jsonl` and a manifest `runs/<run_id>.manifest.json` (git revision, output checksum).

## Evaluate

```bash
python code/evaluation/run_eval.py --split dev        # samples: run + score (regression set, not a holdout)
python code/evaluation/score.py runs/sample.csv dataset/sample_output.csv --split all --diagnostics runs/sample.diagnostics.jsonl
python code/evaluation/run_custom.py                  # synthetic custom cases -> runs/custom/results.{md,json}
python code/tools/discovery_report.py --split all     # end-to-end discovery + account linkage vs samples, miss causes
python code/tools/state_report.py                     # ORACLE-ASSISTED component check (given gold resources/operations)
python code/tools/intent_report.py runs/all.diagnostics.jsonl
# validate an output together with the diagnostics of the run that produced it (blocker flags turn
# "INCOMPLETE without findings" into warnings); for the selected output:
python -c "import sys;sys.path.insert(0,'code');from ghostaudit.validate import cli;cli()" output.csv --diagnostics code/evaluation/final_run/diagnostics.jsonl
```

Reports are rebuilt from preserved, hashed artifacts only (no model calls, no `runs/` dependency):

```bash
# 1. capture evaluation inputs at a committed revision (runs the sample configurations, custom cases, discovery
#    report and test suites; model calls come from the cache where present) -> <bundle>/evaluation_inputs.json
python code/evaluation/capture_inputs.py --bundle-directory code/evaluation/corrective_run
# 2. render (offline). Missing/altered/mismatched inputs exit 1: the final manifest must declare a SHA-256 for
#    output.csv, diagnostics and usage ledger, and each file's raw bytes must match it before it is read (0024).
#    Both reports are rendered before either is written. Stage elsewhere to keep the selected reports.
python code/evaluation/make_reports.py --evaluation-inputs code/evaluation/corrective_run/evaluation_inputs.json \
    --report-output-directory code/evaluation/corrective_run/staged_reports --allow-revision-mismatch
```

Without `--evaluation-inputs`, `make_reports.py` uses the path named by the final manifest's `evaluation_inputs` field.

## Release procedure (spec 0021)

`main.py` writes predictions and diagnostics to run-owned `.<name>.<run_id>.staged` files, validates them, and only then
replaces `--out` and its diagnostics; a failed validation exits 1, leaves the previous files untouched and keeps the
rejected candidate. Non-release configurations cannot target the selected `output.csv` (see Run). `--run-manifest-output PATH` names the
run manifest (revision, uncommitted producing code, SHA-256 of output/diagnostics/usage ledger, validation counts).

```bash
git commit ...                                               # 1. freeze the producing code (clean tree required)
python code/evaluation/capture_inputs.py                     # 2. evaluation inputs at that revision
python code/main.py --cases all --no-cache --out runs/corrective/final_candidate.csv \
    --run-manifest-output runs/corrective/final_candidate.manifest.json      # 3. cold full candidate
python code/tools/finalize_run.py --candidate-manifest runs/corrective/final_candidate.manifest.json \
    --evaluation-inputs code/evaluation/corrective_run/evaluation_inputs.json  # 4. validate + publish the bundle
python code/evaluation/make_reports.py                       # 5. offline rebuild must reproduce the published reports
git add output.csv code/evaluation && python code/tools/make_zip.py   # 6. package the validated tree
```

`finalize_run.py` refuses any candidate whose declared arguments are not the release configuration (sample, any
`--case` selector including an empty one, ablation, ranked accounts, offline), uncommitted-code, altered, incomplete or invalid candidates and
evaluation inputs from another revision; it stages everything first, then replaces `code/evaluation/final_run/`, the
two reports and `output.csv` (last) and re-checks them. The replacement is a sequence of renames, not atomic: an
interruption reports the run id and the previous bundle's location (the last commit remains the recovery point).
`.gitattributes` stores the hashed artifacts (`output.csv`, `final_run/`, `corrective_run/`) byte-exact (`-text`),
so their SHA-256 values also hold on CRLF checkouts. The run manifest reads the Git revision when it is written:
do not commit while a run is in flight.
`--allow-revision-mismatch` is needed only when the evaluation inputs and the selected final run come from different
code revisions; the report is then labelled "NOT a unified release".

## Test

```bash
python -m pytest code/tests -q                      # offline; RUN_LIVE=1 enables the live-model tests
python code/tools/smoke_providers.py   # one live call per provider; prints OK/FAIL only
```
