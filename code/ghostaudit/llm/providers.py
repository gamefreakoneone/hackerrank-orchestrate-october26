"""Shared structured-call layer (TECHNICAL_DESIGN §3.6): cache → model → validation → one repair retry → ledger."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Any, Callable

import yaml
from pydantic import BaseModel, ValidationError

from ghostaudit.config import require_env
from ghostaudit.llm.cache import DiskCache, cache_key
from ghostaudit.llm.hardening import repair_json, validate
from ghostaudit.llm.ledger import UsageLedger

MODELS_PATH = Path(__file__).resolve().parents[2] / "config" / "models.yaml"


class LLMError(RuntimeError):
    """A call failed validation after the repair retry, or the provider failed."""


class LLMUnavailable(LLMError):
    """Offline mode and no cached answer: callers must use their deterministic fallback."""


@dataclass
class TransportResult:
    output: Any                      # dict / str / BaseModel to validate against the schema
    input_tokens: int
    output_tokens: int
    served_model: str


Transport = Callable[..., TransportResult]   # (*, inputs: dict, schema, images) -> TransportResult


def models_config() -> dict:
    return yaml.safe_load(MODELS_PATH.read_text(encoding="utf-8"))


def render_prompt(inputs: dict) -> str:
    prompt = inputs["prompt"]
    if inputs.get("repair_feedback"):
        prompt += ("\n\nYour previous answer did not match the required schema. Validation error:\n"
                   f"{inputs['repair_feedback']}\nAnswer again, following the schema exactly.")
    return prompt


def strands_transport(provider: str, model_id: str, params: dict) -> Transport:
    from strands import Agent

    if provider == "azure":
        from strands.models.openai import OpenAIModel
        endpoint = require_env("AZURE_OPENAI_ENDPOINT").rstrip("/")
        base_url = endpoint + "/" if endpoint.endswith("/openai/v1") else endpoint + "/openai/v1/"
        model = OpenAIModel(client_args={"api_key": require_env("AZURE_OPENAI_API_KEY"), "base_url": base_url},
                            model_id=model_id, params=params)
    elif provider == "gemini":
        from strands.models.gemini import GeminiModel
        model = GeminiModel(client_args={"api_key": require_env("GEMINI_API_KEY")}, model_id=model_id, params=params)
    else:
        raise ValueError(f"unknown Strands provider {provider!r}")

    def call(*, inputs: dict, schema: type[BaseModel], images) -> TransportResult:
        content = [{"text": render_prompt(inputs)}]
        content += [{"image": {"format": "png", "source": {"bytes": Path(p).read_bytes()}}} for p in images]
        agent = Agent(model=model, callback_handler=None, system_prompt=inputs.get("system"))
        try:
            result = agent(content, structured_output_model=schema)
            output = result.structured_output
        except Exception:
            if provider != "gemini":
                raise
            # Gemini fallback: plain JSON text, repaired and validated by the layer
            schema_text = json.dumps(schema.model_json_schema(), sort_keys=True)
            content[0] = {"text": render_prompt(inputs) + f"\n\nReturn only JSON matching this schema:\n{schema_text}"}
            result = Agent(model=model, callback_handler=None, system_prompt=inputs.get("system"))(content)
            output = repair_json(str(result))
        usage = result.metrics.accumulated_usage
        return TransportResult(output=output, input_tokens=int(usage.get("inputTokens", 0)),
                               output_tokens=int(usage.get("outputTokens", 0)), served_model=model_id)

    return call


class LLMLayer:
    """One instance per run. `provider(name)` returns a StructuredCall bound to that provider."""

    def __init__(self, *, ledger_path: Path | None, offline: bool = False, use_cache: bool = True,
                 cache: DiskCache | None = None, transports: dict[str, Transport] | None = None):
        self.offline = offline
        self.use_cache = use_cache
        self.cache = cache or DiskCache()
        self.ledger = UsageLedger(ledger_path)
        self._transports = dict(transports or {})
        self._config = models_config()

    def model_id(self, provider: str) -> str:
        return require_env(self._config["providers"][provider]["model_env"])

    def provider_for_task(self, task: str) -> str:
        return self._config["tasks"][task]

    def _transport(self, provider: str) -> Transport:
        if provider not in self._transports:
            params = self._config["providers"][provider].get("params", {})
            if provider == "jev":
                from ghostaudit.llm.jev import jev_transport
                self._transports[provider] = jev_transport(self.model_id(provider))
            else:
                self._transports[provider] = strands_transport(provider, self.model_id(provider), params)
        return self._transports[provider]

    def provider(self, name: str):
        return partial(self.call, provider=name)

    def call(self, *, task: str, schema: type[BaseModel], inputs: dict, images=(), provider: str | None = None):
        provider = provider or self.provider_for_task(task)
        model = self.model_id(provider)
        key = cache_key(task=task, provider=provider, model=model, schema_json=schema.model_json_schema(),
                        inputs=inputs, image_paths=images)
        if self.use_cache and (entry := self.cache.get(key)) is not None:
            self.ledger.record(provider=provider, model=entry["served_model"], task=task, input_tokens=0,
                               output_tokens=0, cached=True, latency_ms=0)
            return schema.model_validate(entry["value"])
        if self.offline:
            raise LLMUnavailable(f"offline and no cached answer for task {task!r}")
        transport = self._transport(provider)
        started = time.monotonic()
        input_tokens = output_tokens = 0
        attempt_inputs = inputs
        for attempt in (1, 2):
            try:
                result = transport(inputs=attempt_inputs, schema=schema, images=list(images))
            except Exception as error:
                raise LLMError(f"{provider} call failed for task {task!r}: {type(error).__name__}") from error
            input_tokens += result.input_tokens
            output_tokens += result.output_tokens
            try:
                value = validate(schema, result.output)
                break
            except (ValidationError, ValueError) as error:
                if attempt == 2:
                    raise LLMError(f"{provider} output failed validation twice for task {task!r}") from error
                attempt_inputs = {**inputs, "repair_feedback": str(error)[:2000]}
        latency_ms = int((time.monotonic() - started) * 1000)
        self.ledger.record(provider=provider, model=result.served_model, task=task, input_tokens=input_tokens,
                           output_tokens=output_tokens, cached=False, latency_ms=latency_ms, attempts=attempt)
        # written even under --no-cache (which only skips reads) so a cold run leaves a reproducible cache
        self.cache.put(key, {"value": value.model_dump(mode="json"), "served_model": result.served_model})
        return value
