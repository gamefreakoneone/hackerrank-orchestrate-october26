# Spec 0001 — scaffold-env-logging: status

**Status:** Completed (2026-10-25, overnight run)

## Evidence

```text
$ pip install -r code/requirements.txt          # exit 0 (all pins already satisfied)
$ python code/main.py && python -c "...assert len(r)==518..."
wrote 518 rows to <repo>/output.csv (format-only baseline)
rows 518
$ python -m pytest code/tests -q
1 passed
$ python code/tools/smoke_providers.py
jev: OK model=jev-1.14.0 p_yes=0.86
azure: OK deletion_requested=True
gemini: OK reply_chars=6
```

Scorer metrics: not measured (scorer arrives in spec 0005).

## Notes

- `strands-agents` pinned with `[openai,gemini]` extras; versions are the exact installed ones.
- Azure deployment `AZURE_DEPLOYMENT_FALLBACK` rejects function tools on `/chat/completions` while reasoning is
  enabled (400 `reasoning_effort`); Strands `OpenAIModel` gets `params={"reasoning_effort": "none"}`. Base URL =
  `AZURE_OPENAI_ENDPOINT` + `/openai/v1/` unless already present.
- TypeSafe SDK reads `TYPESAFE_BASE_URL`; our env var is `TYPESAFE_API_BASE`, passed explicitly as `base_url`.
- Root `output.csv` written by the stub is a **format-only baseline**, left untracked.
