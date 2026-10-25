"""TypeSafe Jev transport: typed Choice / Noul questions over a JSON state (typesafe-sdk)."""
from __future__ import annotations

from ghostaudit.config import require_env
from ghostaudit.llm.providers import TransportResult


def jev_transport(model_id: str):
    from typesafe_sdk import Choice, Noul, TypeSafeClient

    client = TypeSafeClient(api_key=require_env("TYPESAFE_API_KEY"), base_url=require_env("TYPESAFE_API_BASE"))

    def call(*, inputs: dict, schema, images) -> TransportResult:
        """inputs = {"state": {...}, "questions": {name: {"type": "choice"|"noul", "instructions", "criteria"}}}."""
        questions = {}
        for name, spec in inputs["questions"].items():
            if spec["type"] == "choice":
                questions[name] = Choice(instructions=spec["instructions"], criteria=spec["criteria"])
            else:
                questions[name] = Noul(instructions=spec["instructions"], criteria=spec.get("criteria"))
        response = client.system_one(state=inputs["state"], questions=questions, model=model_id)
        output = {}
        for name, answer in response.answers.items():
            if answer.type == "choice":
                output[name] = {"choice": answer.choice, "confidence": answer.confidence,
                                "probabilities": dict(answer.probabilities)}
            else:
                output[name] = {"noul": answer.noul}
        return TransportResult(output=output, input_tokens=response.usage.input_tokens or 0,
                               output_tokens=response.usage.output_tokens or 0, served_model=response.model)

    return call
