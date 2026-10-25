"""One minimal live call per provider. Prints only `provider: OK|FAIL <error class>`; never keys or raw output."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pydantic import BaseModel  # noqa: E402

from ghostaudit.config import require_env  # noqa: E402


class DeletionRequestedAnswer(BaseModel):
    deletion_requested: bool


def azure_openai_v1_base_url(endpoint: str) -> str:
    """Azure resource endpoints are OpenAI-compatible under /openai/v1/."""
    endpoint = endpoint.rstrip("/")
    return endpoint + "/" if endpoint.endswith("/openai/v1") else endpoint + "/openai/v1/"


def smoke_jev() -> str:
    from typesafe_sdk import Noul, TypeSafeClient

    with TypeSafeClient(api_key=require_env("TYPESAFE_API_KEY"), base_url=require_env("TYPESAFE_API_BASE")) as client:
        response = client.system_one(
            state={"request_text": "Please delete my account."},
            questions={"asks_for_deletion": Noul(instructions="Does `request_text` ask to delete personal data?")},
            model=require_env("JEV_MODEL"),
        )
    probability_yes = response.nouls["asks_for_deletion"].noul
    return f"model={response.model} p_yes={probability_yes:.2f}"


def smoke_azure() -> str:
    from strands import Agent
    from strands.models.openai import OpenAIModel

    model = OpenAIModel(
        client_args={"api_key": require_env("AZURE_OPENAI_API_KEY"),
                     "base_url": azure_openai_v1_base_url(require_env("AZURE_OPENAI_ENDPOINT"))},
        model_id=require_env("AZURE_DEPLOYMENT_FALLBACK"),
        # The deployment rejects function tools (Strands structured output) unless reasoning is off.
        params={"reasoning_effort": "none"},
    )
    result = Agent(model=model, callback_handler=None)(
        "Request: 'Please delete my account.' Does it ask for deletion?",
        structured_output_model=DeletionRequestedAnswer,
    )
    return f"deletion_requested={result.structured_output.deletion_requested}"


def smoke_gemini() -> str:
    from strands import Agent
    from strands.models.gemini import GeminiModel

    model = GeminiModel(client_args={"api_key": require_env("GEMINI_API_KEY")},
                        model_id=require_env("GEMINI_VISION_MODEL"))
    result = Agent(model=model, callback_handler=None)("Reply with the single word: ready")
    return f"reply_chars={len(str(result))}"


def main() -> int:
    failures = 0
    for provider_name, smoke in (("jev", smoke_jev), ("azure", smoke_azure), ("gemini", smoke_gemini)):
        try:
            detail = smoke()
            print(f"{provider_name}: OK {detail}")
        except Exception as error:  # report the class only; messages may echo endpoints
            failures += 1
            print(f"{provider_name}: FAIL {type(error).__name__}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
