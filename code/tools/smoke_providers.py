"""One minimal live call per provider through the shared LLM layer (no cache, no ledger file).

Prints only `provider: OK|FAIL <error class>`; never keys, endpoints or raw responses.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pydantic import BaseModel  # noqa: E402

from ghostaudit.llm.providers import LLMLayer  # noqa: E402


class DeletionRequestedAnswer(BaseModel):
    deletion_requested: bool


class JevSmokeAnswer(BaseModel):
    asks_for_deletion: dict


def main() -> int:
    layer = LLMLayer(ledger_path=None, use_cache=False)
    calls = {
        "jev": lambda: layer.call(task="smoke", provider="jev", schema=JevSmokeAnswer, inputs={
            "state": {"request_text": "Please delete my account."},
            "questions": {"asks_for_deletion": {"type": "noul",
                                                "instructions": "Does `request_text` ask to delete personal data?"}}}),
        "azure": lambda: layer.call(task="smoke", provider="azure", schema=DeletionRequestedAnswer, inputs={
            "prompt": "Request: 'Please delete my account.' Does it ask for deletion?"}),
        "gemini": lambda: layer.call(task="smoke", provider="gemini", schema=DeletionRequestedAnswer, inputs={
            "prompt": "Request: 'Please delete my account.' Does it ask for deletion?"}),
    }
    failures = 0
    for provider_name, call in calls.items():
        try:
            call()
            row = layer.ledger.rows[-1]
            print(f"{provider_name}: OK model={row['model']} tokens={row['input_tokens']}+{row['output_tokens']}")
        except Exception as error:   # class only: messages may echo endpoints
            failures += 1
            print(f"{provider_name}: FAIL {type(error).__name__}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
