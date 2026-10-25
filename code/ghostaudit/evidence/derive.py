"""Shared derivation for all parsers: system_id, category, identifiers, field normalization."""
from __future__ import annotations

import re
from datetime import datetime
from functools import cache
from pathlib import Path

import yaml

from ghostaudit.evidence.model import Observation, SourceKind
from ghostaudit.identity import normalize_email, normalize_name, normalize_phone

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "categories.yaml"
RESOURCE_RE = re.compile(
    r"\b(?:account|search|support|analytics|cache|export|data_flow|backup|legal_hold|"
    r"tombstone|audit_record|email_delivery|object|marketing)_\d+\b")
EMAIL_TOKEN_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
HASH_TOKEN_RE = re.compile(r"(?<![0-9a-fA-F])[0-9a-fA-F]{64}(?![0-9a-fA-F])")
USER_TOKEN_RE = re.compile(r"\buser_\d+\b")
PHONE_TOKEN_RE = re.compile(r"(?<![\w+])\+\d[\d\s().-]{5,}\d(?!\d)")


@cache
def config() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


def system_for_resource(resource_id: str) -> str | None:
    prefix = resource_id.rsplit("_", 1)[0]
    return config()["resource_prefix_system"].get(prefix)


def is_resource_id(value: str | None) -> bool:
    return bool(value) and RESOURCE_RE.fullmatch(value) is not None


def normalize_value(name: str, value) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    text = str(value).strip()
    if text.lower() in ("null", "none", ""):
        return None
    if name.rsplit(".", 1)[-1] in config()["boolean_fields"]:
        lowered = text.lower()
        if lowered in ("1", "true", "yes"):
            return "true"
        if lowered in ("0", "false", "no"):
            return "false"
    return text


def flatten(record: dict, prefix: str = "") -> dict[str, str | None]:
    """Nested dicts/lists → dotted keys; values normalized (None = null)."""
    flat: dict[str, str | None] = {}
    for key, value in record.items():
        path = f"{prefix}{key}"
        if isinstance(value, dict):
            flat.update(flatten(value, f"{path}."))
        elif isinstance(value, list):
            if all(isinstance(item, dict) for item in value) and value:
                for index, item in enumerate(value):
                    flat.update(flatten(item, f"{path}.{index}."))
            else:
                flat[path] = ",".join(str(item) for item in value) if value else None
        else:
            flat[path] = normalize_value(path, value)
    return flat


def extract_identifiers(fields: dict[str, str | None]) -> frozenset[str]:
    """Normalized identifier values (emails lower, hashes lower, user ids, phone digits, NFC names)."""
    found: set[str] = set()
    name_fields = set(config()["name_fields"])
    for key, value in fields.items():
        if not value:
            continue
        leaf = key.rsplit(".", 1)[-1]
        found.update(normalize_email(m) for m in EMAIL_TOKEN_RE.findall(value))
        found.update(m.lower() for m in HASH_TOKEN_RE.findall(value))
        found.update(USER_TOKEN_RE.findall(value))
        found.update(normalize_phone(m) for m in PHONE_TOKEN_RE.findall(value))
        if "phone" in leaf:
            found.add(normalize_phone(value))
        if leaf in name_fields:
            found.add(normalize_name(value))
    return frozenset(v for v in found if v)


def category_for(record_type: str | None, container: str | None, event_names: list[str] | None = None) -> str | None:
    cfg = config()
    if record_type:
        return record_type
    if container and container in cfg["container_category"]:
        return cfg["container_category"][container]
    for event_name in event_names or []:
        if event_name in cfg["log_event_category"]:
            return cfg["log_event_category"][event_name]
    return None


def make_observation(*, evidence_id: str, captured_at: datetime, source_kind: SourceKind, container: str,
                     physical_copy: str, resource_id: str, fields: dict[str, str | None],
                     observed_at: datetime | None = None, system_id: str | None = None,
                     event_names: list[str] | None = None) -> Observation:
    return Observation(
        evidence_id=evidence_id, captured_at=captured_at, observed_at=observed_at, source_kind=source_kind,
        container=container, physical_copy=physical_copy,
        system_id=system_id or system_for_resource(resource_id), resource_id=resource_id,
        category=category_for(fields.get("record_type"), container, event_names),
        identifiers=extract_identifiers(fields), fields=fields)
