"""Plain-text handover records: rows `- ts | system | resource | RECORD_TYPE | STATE | identifier`."""
from __future__ import annotations

from datetime import datetime

from ghostaudit.evidence.derive import is_resource_id, make_observation, normalize_value
from ghostaudit.evidence.model import Observation
from ghostaudit.evidence.sql import optional_ts

ROW_FIELDS = ("observed_at", "system", "resource_id", "record_type", "result", "subject_identifier")


def parse_text(file_id: str, captured_at: datetime, text: str) -> list[Observation]:
    observations = []
    for line in text.splitlines():
        if not line.startswith("- ") or line.count("|") != 5:
            continue
        values = [part.strip() for part in line[2:].split("|")]
        fields = {name: normalize_value(name, value) for name, value in zip(ROW_FIELDS, values)}
        if not is_resource_id(fields["resource_id"]):
            continue
        observations.append(make_observation(
            evidence_id=file_id, captured_at=captured_at, source_kind="txt", container="handover",
            physical_copy="service_read", resource_id=fields["resource_id"], fields=fields,
            observed_at=optional_ts(fields["observed_at"]), system_id=fields["system"]))
    return observations
