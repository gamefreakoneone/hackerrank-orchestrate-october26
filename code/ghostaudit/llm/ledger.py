"""Usage ledger: one JSONL row per structured call; summarize() totals per model and overall."""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import yaml

PRICING_PATH = Path(__file__).resolve().parents[2] / "config" / "pricing.yaml"


class UsageLedger:
    def __init__(self, path: Path | None):
        self.path = path
        self.rows: list[dict] = []

    def record(self, *, provider: str, model: str, task: str, input_tokens: int, output_tokens: int,
               cached: bool, latency_ms: int, attempts: int = 1) -> None:
        row = {"provider": provider, "model": model, "task": task, "input_tokens": input_tokens,
               "output_tokens": output_tokens, "cached": cached, "latency_ms": latency_ms, "attempts": attempts}
        self.rows.append(row)
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(row, sort_keys=True) + "\n")


def load_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def summarize(rows: list[dict], pricing_path: Path = PRICING_PATH) -> dict:
    """{'per_model': {(provider, model): totals}, 'overall': totals}; cost None when a price is unknown."""
    prices = (yaml.safe_load(pricing_path.read_text(encoding="utf-8")) or {}).get("models") or {}
    per_model: dict[tuple[str, str], dict] = defaultdict(lambda: {"calls": 0, "cached_calls": 0, "attempts": 0,
                                                                   "input_tokens": 0, "output_tokens": 0})
    for row in rows:
        totals = per_model[(row["provider"], row["model"])]
        if row["cached"]:
            totals["cached_calls"] += 1
        else:
            totals["calls"] += 1
            totals["attempts"] += row.get("attempts", 1)
            totals["input_tokens"] += row["input_tokens"]
            totals["output_tokens"] += row["output_tokens"]
    overall = {"calls": 0, "cached_calls": 0, "attempts": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}
    for (provider, model), totals in per_model.items():
        price = prices.get(model)
        if price and price.get("input_per_million") is not None and price.get("output_per_million") is not None:
            totals["cost_usd"] = (totals["input_tokens"] * price["input_per_million"]
                                  + totals["output_tokens"] * price["output_per_million"]) / 1_000_000
        else:
            totals["cost_usd"] = None
        for key in ("calls", "cached_calls", "attempts", "input_tokens", "output_tokens"):
            overall[key] += totals[key]
        if totals["cost_usd"] is None or overall["cost_usd"] is None:
            overall["cost_usd"] = None
        else:
            overall["cost_usd"] += totals["cost_usd"]
    return {"per_model": dict(sorted(per_model.items())), "overall": overall}
