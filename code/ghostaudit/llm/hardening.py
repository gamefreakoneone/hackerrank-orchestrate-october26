"""Output hardening: tolerant JSON extraction and schema validation."""
from __future__ import annotations

import json
import re

from pydantic import BaseModel

FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.S)


def repair_json(text: str):
    """Parse model text that should be JSON: strips code fences and surrounding prose."""
    text = text.strip()
    fenced = FENCE_RE.search(text)
    if fenced:
        text = fenced.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        starts = [i for i in (text.find("{"), text.find("[")) if i >= 0]
        if not starts:
            raise
        start = min(starts)
        end = max(text.rfind("}"), text.rfind("]"))
        return json.loads(text[start:end + 1])


def validate(schema: type[BaseModel], data) -> BaseModel:
    if isinstance(data, schema):
        return data
    if isinstance(data, BaseModel):
        data = data.model_dump(mode="json")
    if isinstance(data, str):
        data = repair_json(data)
    return schema.model_validate(data)
