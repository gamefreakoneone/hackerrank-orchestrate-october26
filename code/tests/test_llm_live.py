"""Opt-in live test: RUN_LIVE=1 python -m pytest code/tests/test_llm_live.py -q (makes 3 tiny paid calls)."""
import os

import pytest
from pydantic import BaseModel

from ghostaudit.llm.providers import LLMLayer

pytestmark = pytest.mark.skipif(os.environ.get("RUN_LIVE") != "1", reason="set RUN_LIVE=1 for live provider calls")


class DeletionAnswer(BaseModel):
    deletion_requested: bool


def test_live_providers(tmp_path):
    layer = LLMLayer(ledger_path=tmp_path / "usage.jsonl", use_cache=False)
    for provider in ("azure", "gemini"):
        answer = layer.call(task="live_smoke", schema=DeletionAnswer, provider=provider,
                            inputs={"prompt": "Request: 'Please erase my account.' Does it ask for deletion?"})
        assert answer.deletion_requested is True

    class JevAnswer(BaseModel):
        asks_for_deletion: dict

    jev = layer.call(task="live_smoke", schema=JevAnswer, provider="jev", inputs={
        "state": {"request_text": "Please erase my account."},
        "questions": {"asks_for_deletion": {"type": "noul",
                                            "instructions": "Does `request_text` ask to delete personal data?"}}})
    assert jev.asks_for_deletion["noul"] > 0.5
    assert all(not row["cached"] and row["input_tokens"] > 0 for row in layer.ledger.rows)
