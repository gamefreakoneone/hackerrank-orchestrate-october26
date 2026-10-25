"""Typed, timezone-aware loaders for the participant CSVs. Never opens sample_output.csv."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ghostaudit.models import Activity, AuditEvent, EvidenceFile, Identity, Request, Rule, case_key


def parse_ts(text: str) -> datetime:
    parsed = datetime.fromisoformat(text.strip().replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"timestamp without timezone: {text!r}")
    return parsed.astimezone(timezone.utc)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


@dataclass(frozen=True)
class Dataset:
    dataset_dir: Path
    requests: list[Request]                 # sorted by case number
    identities: dict[str, Identity]         # user_id -> current snapshot
    audit: list[AuditEvent]                 # sorted by (event_time, audit_id)
    activity: list[Activity]                # sorted by (event_time, activity_id)
    rules: dict[str, Rule]                  # data_category -> rule
    evidence: dict[str, EvidenceFile]       # file_id -> manifest row

    def evidence_path(self, file_id: str) -> Path:
        return self.dataset_dir / self.evidence[file_id].file_path


def _timestamped(row: dict[str, str], *names: str) -> dict:
    return {**row, **{name: parse_ts(row[name]) for name in names}}


def load_dataset(dataset_dir: Path, sample: bool = False) -> Dataset:
    requests_file = "sample_deletion_requests.csv" if sample else "deletion_requests.csv"
    requests = [Request(**_timestamped(r, "requested_at", "reported_at", "audit_at"))
                for r in read_csv(dataset_dir / requests_file)]
    requests.sort(key=lambda r: case_key(r.case_id))
    identities = {r["user_id"]: Identity(**_timestamped(r, "updated_at"))
                  for r in read_csv(dataset_dir / "user_identities.csv")}
    audit = sorted((AuditEvent(**_timestamped(r, "event_time")) for r in read_csv(dataset_dir / "user_audit_log.csv")),
                   key=lambda a: (a.event_time, a.audit_id))
    activity = sorted((Activity(**_timestamped(r, "event_time")) for r in read_csv(dataset_dir / "system_activity.csv")),
                      key=lambda a: (a.event_time, a.activity_id))
    rules = {r["data_category"]: Rule(**r) for r in read_csv(dataset_dir / "deletion_rules.csv")}
    evidence = {r["file_id"]: EvidenceFile(**_timestamped(r, "captured_at"))
                for r in read_csv(dataset_dir / "evidence_files.csv")}
    missing = [f.file_path for f in evidence.values() if not (dataset_dir / f.file_path).is_file()]
    if missing:
        raise FileNotFoundError(f"manifest files missing under {dataset_dir}: {missing[:5]}")
    return Dataset(dataset_dir, requests, identities, audit, activity, rules, evidence)
