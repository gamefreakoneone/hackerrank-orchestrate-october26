"""Deterministic output writer: canonical step order, consecutive step_no, compact sorted-key JSON."""
from __future__ import annotations

import csv
import json
from pathlib import Path

from ghostaudit.models import OP_ORDER, Status, Step, case_key

OUTPUT_HEADER = ["case_id", "deletion_status", "steps_json"]


def canonical(steps: list[Step]) -> list[Step]:
    ordered = sorted(steps, key=lambda s: (OP_ORDER[s.operation], s.system_id, s.resource_id))
    return [step.model_copy(update={"step_no": number}) for number, step in enumerate(ordered, start=1)]


def dumps_steps(steps: list[Step]) -> str:
    return json.dumps([step.model_dump(mode="json") for step in canonical(steps)],
                      sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def write_output(rows: list[tuple[str, Status, list[Step]]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(OUTPUT_HEADER)
        for case_id, status, steps in sorted(rows, key=lambda row: case_key(row[0])):
            writer.writerow([case_id, Status(status).value, dumps_steps(steps)])
