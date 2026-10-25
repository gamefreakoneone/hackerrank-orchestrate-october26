"""Disk cache for structured LLM results: code/.cache/llm/<sha256>.json (gitignored)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

DEFAULT_CACHE_DIR = Path(__file__).resolve().parents[2] / ".cache" / "llm"


def canonical_json(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def cache_key(*, task: str, provider: str, model: str, schema_json: dict, inputs: dict, image_paths=()) -> str:
    image_hashes = [hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in image_paths]
    material = canonical_json({"task": task, "provider": provider, "model": model, "schema": schema_json,
                               "inputs": inputs, "images": image_hashes})
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


class DiskCache:
    def __init__(self, directory: Path = DEFAULT_CACHE_DIR):
        self.directory = directory

    def get(self, key: str) -> dict | None:
        path = self.directory / f"{key}.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None

    def put(self, key: str, entry: dict) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        (self.directory / f"{key}.json").write_text(canonical_json(entry), encoding="utf-8")
