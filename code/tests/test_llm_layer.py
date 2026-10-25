import pytest
from pydantic import BaseModel

from ghostaudit.llm.cache import DiskCache
from ghostaudit.llm.hardening import repair_json
from ghostaudit.llm.ledger import load_rows, summarize
from ghostaudit.llm.providers import LLMError, LLMLayer, LLMUnavailable, TransportResult


class Verdict(BaseModel):
    label: str
    score: float


class FakeTransport:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = []

    def __call__(self, *, inputs, schema, images):
        self.calls.append(inputs)
        return TransportResult(output=self.outputs.pop(0), input_tokens=10, output_tokens=3, served_model="fake-1")


@pytest.fixture(autouse=True)
def model_env(monkeypatch):
    monkeypatch.setenv("AZURE_DEPLOYMENT_FALLBACK", "fake-deployment")


def make_layer(tmp_path, transport, **kwargs):
    return LLMLayer(ledger_path=tmp_path / "usage.jsonl", cache=DiskCache(tmp_path / "cache"),
                    transports={"azure": transport}, **kwargs)


def test_cache_hit_skips_the_model(tmp_path):
    transport = FakeTransport([{"label": "DELETION", "score": 0.9}])
    layer = make_layer(tmp_path, transport)
    first = layer.call(task="t", schema=Verdict, inputs={"prompt": "x"}, provider="azure")
    second = layer.call(task="t", schema=Verdict, inputs={"prompt": "x"}, provider="azure")
    assert first == second and len(transport.calls) == 1
    assert [row["cached"] for row in load_rows(tmp_path / "usage.jsonl")] == [False, True]


def test_one_repair_retry_then_success(tmp_path):
    transport = FakeTransport(['{"label": "DELETION"}', '```json\n{"label": "DELETION", "score": 1}\n```'])
    layer = make_layer(tmp_path, transport)
    assert layer.call(task="t", schema=Verdict, inputs={"prompt": "x"}, provider="azure").score == 1.0
    assert "repair_feedback" in transport.calls[1]
    (row,) = load_rows(tmp_path / "usage.jsonl")
    assert row["attempts"] == 2 and row["input_tokens"] == 20


def test_second_validation_failure_raises(tmp_path):
    layer = make_layer(tmp_path, FakeTransport(['{"label": 1}', "not json"]))
    with pytest.raises(LLMError):
        layer.call(task="t", schema=Verdict, inputs={"prompt": "x"}, provider="azure")


def test_offline_without_cache_is_unavailable(tmp_path):
    layer = make_layer(tmp_path, FakeTransport([]), offline=True)
    with pytest.raises(LLMUnavailable):
        layer.call(task="t", schema=Verdict, inputs={"prompt": "x"}, provider="azure")


def test_no_cache_skips_reads(tmp_path):
    transport = FakeTransport([{"label": "A", "score": 0}, {"label": "B", "score": 0}])
    make_layer(tmp_path, transport).call(task="t", schema=Verdict, inputs={"prompt": "x"}, provider="azure")
    cold = make_layer(tmp_path, transport, use_cache=False)
    assert cold.call(task="t", schema=Verdict, inputs={"prompt": "x"}, provider="azure").label == "B"


def test_ledger_summary_sums_per_model(tmp_path):
    rows = [{"provider": "azure", "model": "m1", "task": "t", "input_tokens": 10, "output_tokens": 2, "cached": False,
             "latency_ms": 5, "attempts": 1},
            {"provider": "azure", "model": "m1", "task": "t", "input_tokens": 0, "output_tokens": 0, "cached": True,
             "latency_ms": 0},
            {"provider": "jev", "model": "j1", "task": "t", "input_tokens": 7, "output_tokens": 1, "cached": False,
             "latency_ms": 5, "attempts": 1}]
    pricing = tmp_path / "pricing.yaml"
    pricing.write_text("models:\n  m1: {input_per_million: 1.0, output_per_million: 2.0}\n")
    summary = summarize(rows, pricing)
    assert summary["per_model"][("azure", "m1")]["calls"] == 1
    assert summary["per_model"][("azure", "m1")]["cached_calls"] == 1
    assert summary["per_model"][("azure", "m1")]["cost_usd"] == pytest.approx(14 / 1_000_000)
    assert summary["per_model"][("jev", "j1")]["cost_usd"] is None
    assert summary["overall"]["input_tokens"] == 17 and summary["overall"]["cost_usd"] is None


def test_repair_json_strips_prose():
    assert repair_json('Here you go: {"a": [1, 2]} thanks') == {"a": [1, 2]}
