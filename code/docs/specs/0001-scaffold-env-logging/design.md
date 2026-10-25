# Spec 0001 — scaffold-env-logging: design

Contracts: `code/docs/TECHNICAL_DESIGN.md` §3. Data facts: §5.

- `code/main.py`: argparse per TECHNICAL_DESIGN §3.7 (flags accepted, most no-op for now);
  `ROOT = Path(__file__).resolve().parents[1]`; read `dataset/deletion_requests.csv` with `csv.DictReader`;
  sort by `int(case_id.split("_")[1])`; write with `csv.writer(lineterminator="\n")`.
- `code/ghostaudit/__init__.py` (empty package) and `code/ghostaudit/config.py`:
  `def env(name: str, default: str | None = None) -> str | None` reading `os.environ` after an optional
  `.env` load (tiny parser, no new dependency; never logs values).
- `code/tools/smoke_providers.py`:
  - Jev: `typesafe-sdk` client with `TYPESAFE_API_KEY`/`TYPESAFE_API_BASE`, one yes/no question on "Please delete my account".
    Check the TypeSafe skill (`typesafe:typesafe-ai`) and https://docs.typesafe.ai for the current call shape.
  - Azure: Strands `OpenAIModel(client_args={"api_key":..., "base_url": AZURE_OPENAI_ENDPOINT}, model_id=AZURE_DEPLOYMENT_FALLBACK)`;
    one structured-output call with a 1-field pydantic model. Do not pass `temperature` if the deployment rejects it.
  - Gemini: Strands `GeminiModel(client_args={"api_key":...}, model_id=GEMINI_VISION_MODEL)`; one text call.
  - Each wrapped in try/except; print only provider name + OK/FAIL + exception class name.
- `.gitignore` already covers `.env`, caches, `runs/`, `code.zip`.
