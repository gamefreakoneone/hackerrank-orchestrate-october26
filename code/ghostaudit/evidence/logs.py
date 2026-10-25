"""Log files (six line formats) → one Observation per resource per trace_id group (or standalone line)."""
from __future__ import annotations

import json
import re
from datetime import datetime

from ghostaudit.evidence.derive import extract_identifiers, is_resource_id, make_observation, normalize_value
from ghostaudit.evidence.model import Observation
from ghostaudit.evidence.sql import optional_ts

KV_RE = re.compile(r'([A-Za-z_][\w.]*)=("(?:[^"\\]|\\.)*"|\S+)')
BRACKET_RE = re.compile(r"^\[(\w+)\] \[([^\]]+)\] \[([^\]]+)\] (\w+):\s?(.*)$")
PIPE_RE = re.compile(r"^\|\s*(\w+)\s*\|\s*(\S+)\s*\|\s*(\S+)\s*\|\s*(\S+)\s*\|\s*(.*)$")
TRACE_ID_RE = re.compile(r"^(?:tr|rb)-[\w-]+$")


def parse_kv(text: str) -> dict[str, str]:
    pairs = {}
    for key, value in KV_RE.findall(text):
        if value.startswith('"') and value.endswith('"') and len(value) >= 2:
            value = value[1:-1].replace('\\"', '"')
        pairs[key] = value
    return pairs


def parse_line(line: str) -> dict[str, str] | None:
    """→ {ts, service, trace_id?, event?, ...kv} or None for non-log lines."""
    head, _, rest = line.strip().partition(" ")
    if not rest or optional_ts(head) is None:
        return None
    rest = rest.strip()
    record: dict[str, str]
    if rest.startswith("{"):
        record = {k: str(v) for k, v in json.loads(rest).items() if v is not None}
        record.setdefault("service", record.get("logger", ""))
    elif rest.startswith("<"):
        parts = rest.split(maxsplit=6)
        record = {"service": parts[2], "trace_id": parts[3], **parse_kv(parts[6] if len(parts) > 6 else "")}
    elif (match := BRACKET_RE.match(rest)) or (match := PIPE_RE.match(rest)):
        level, service, trace_id, event, tail = match.groups()
        record = {"level": level, "service": service, "trace_id": trace_id, "event": event, **parse_kv(tail)}
    else:
        record = parse_kv(rest)
        if "message" in record and "function" in record:             # cloud format: kv nested in message
            record = {"service": record["function"], "trace_id": record.get("requestId", ""),
                      **{k: v for k, v in record.items() if k not in ("message", "function", "requestId")},
                      **parse_kv(record["message"])}
    record["ts"] = head
    if not TRACE_ID_RE.match(record.get("trace_id", "")):
        record.pop("trace_id", None)
    return record


def parse_log(file_id: str, captured_at: datetime, text: str) -> list[Observation]:
    groups: dict[str, list[dict[str, str]]] = {}
    for number, line in enumerate(text.splitlines()):
        record = parse_line(line)
        if record is not None:
            groups.setdefault(record.get("trace_id") or f"line-{number}", []).append(record)
    observations = []
    for group_key, records in groups.items():
        resource_ids = sorted({r[k] for r in records for k in ("resource_id", "lookup_key") if is_resource_id(r.get(k))})
        if not resource_ids:
            continue
        merged: dict[str, str | None] = {}
        for record in records:
            merged.update({k: normalize_value(k, v) for k, v in record.items() if k != "ts"})
        events = [r["event"] for r in records if r.get("event")]
        merged["events"] = ",".join(events)
        merged["trace_group"] = group_key
        identifiers = frozenset().union(*(extract_identifiers({k: normalize_value(k, v) for k, v in r.items()})
                                          for r in records))
        for resource_id in resource_ids:
            observation = make_observation(
                evidence_id=file_id, captured_at=captured_at, source_kind="log", container=merged.get("service") or "",
                physical_copy="service_read", resource_id=resource_id, fields=dict(merged),
                observed_at=optional_ts(records[-1]["ts"]), event_names=events)
            observations.append(observation.model_copy(update={"identifiers": identifiers}))
    return observations
