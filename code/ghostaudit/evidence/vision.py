"""PNG screenshots → Observations via one cached Gemini call per file (spec 0009), regex-revalidated."""
from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from pydantic import BaseModel

from ghostaudit.evidence.derive import config, is_resource_id, make_observation, normalize_value, system_for_resource
from ghostaudit.evidence.model import Observation
from ghostaudit.identity import EMAIL_RE, HASH_RE, PHONE_RE, USER_ID_RE, normalize_email
from ghostaudit.llm.providers import LLMLayer, LLMUnavailable
from ghostaudit.loaders import Dataset

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "vision_extract.md"


class VisionRecord(BaseModel):
    resource_id: str
    system_hint: str | None = None
    record_type: str | None = None
    subject_identifiers: list[str] = []
    status_text: str | None = None
    timestamp: str | None = None


class VisionExtraction(BaseModel):
    records: list[VisionRecord]


def identity_email_universe(dataset: Dataset) -> set[str]:
    emails = {normalize_email(i.email) for i in dataset.identities.values()}
    emails |= {normalize_email(v) for a in dataset.audit if a.field_name == "email" for v in (a.old_value, a.new_value)}
    return emails


def valid_identifier(value: str, email_universe: set[str]) -> bool:
    value = value.strip()
    if EMAIL_RE.match(value):
        return normalize_email(value) in email_universe
    return bool(HASH_RE.match(value) or USER_ID_RE.match(value) or
                (PHONE_RE.match(value) and len(re.sub(r"\D", "", value)) >= 7))


def status_fields(status_text: str | None) -> dict[str, str]:
    lowered = (status_text or "").lower()
    for rule in config()["png_status_fields"]:
        if rule["match"] in lowered:
            return {rule["field"]: rule["value"]}
    return {}


def revalidate(file_id: str, captured_at, origin: str, extraction: VisionExtraction, email_universe: set[str],
               counts: Counter) -> list[Observation]:
    observations = []
    screen_system, screen_category = config()["png_origin_category"].get(origin, (None, None))
    for record in extraction.records:
        resource_id = record.resource_id.strip()
        if not is_resource_id(resource_id):
            counts["dropped_resource_id"] += 1
            continue
        category = screen_category if system_for_resource(resource_id) == screen_system else None
        identifiers = [v for v in record.subject_identifiers if valid_identifier(v, email_universe)]
        counts["dropped_identifier"] += len(record.subject_identifiers) - len(identifiers)
        fields = {"record_type": category, "screen_record_type": normalize_value("x", record.record_type),
                  "system_hint": normalize_value("x", record.system_hint),
                  "status_text": normalize_value("x", record.status_text),
                  "timestamp": normalize_value("x", record.timestamp),
                  "subject_identifiers": ",".join(identifiers) or None, **status_fields(record.status_text)}
        observations.append(make_observation(evidence_id=file_id, captured_at=captured_at, source_kind="png",
                                             container=origin, physical_copy="screen", resource_id=resource_id,
                                             fields=fields))
        counts["records"] += 1
    return observations


def vision_observations(dataset: Dataset, layer: LLMLayer | None = None, offline: bool = False,
                        report: dict | None = None) -> list[Observation]:
    """One structured Gemini call per PNG (cached). A PNG with no answer offline is missing evidence, not absence."""
    layer = layer or LLMLayer(ledger_path=None, offline=offline)
    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    email_universe = identity_email_universe(dataset)
    observations = []
    for file_id, evidence_file in sorted(dataset.evidence.items()):
        path = dataset.evidence_path(file_id)
        if path.suffix != ".png":
            continue
        counts: Counter = Counter()
        try:
            extraction = layer.call(task="vision_extract", schema=VisionExtraction, inputs={"prompt": prompt},
                                    images=[path])
        except LLMUnavailable:
            counts["unavailable"] += 1
            extraction = VisionExtraction(records=[])
        observations += revalidate(file_id, evidence_file.captured_at, evidence_file.origin, extraction,
                                   email_universe, counts)
        if report is not None:
            report[file_id] = dict(counts)
    return observations
