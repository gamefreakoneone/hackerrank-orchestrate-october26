"""Evidence ledger: parse every non-image file once (cached by content hash + parser version) and index it."""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from ghostaudit.evidence.json_ import parse_json
from ghostaudit.evidence.logs import parse_log
from ghostaudit.evidence.model import Observation, SnapshotCoverage
from ghostaudit.evidence.pdf import parse_pdf, pdf_text
from ghostaudit.evidence.sql import parse_sql
from ghostaudit.evidence.text import parse_text
from ghostaudit.loaders import Dataset
from ghostaudit.models import Activity

PARSER_VERSION = "0012.1"
CACHE_DIR = Path(__file__).resolve().parents[2] / ".cache" / "evidence"
STATE_CHECK_EVENT_TYPES = ("CHECK_DATA_FLOW", "CHECK_RESTORE_ACCESS")


@dataclass
class Ledger:
    observations: list[Observation] = field(default_factory=list)
    coverage: list[SnapshotCoverage] = field(default_factory=list)
    empty_files: dict[str, str] = field(default_factory=dict)       # file_id -> reason
    by_resource: dict[str, list[Observation]] = field(default_factory=lambda: defaultdict(list))
    by_identifier: dict[str, list[Observation]] = field(default_factory=lambda: defaultdict(list))
    coverage_by_system: dict[str, list[SnapshotCoverage]] = field(default_factory=lambda: defaultdict(list))

    def add(self, observations: list[Observation], coverage: list[SnapshotCoverage]) -> None:
        self.observations += observations
        self.coverage += coverage

    def build_indexes(self) -> None:
        self.observations.sort(key=lambda o: (o.captured_at, o.evidence_id, o.resource_id))
        self.coverage.sort(key=lambda c: (c.captured_at, c.file_id, c.collection, c.physical_copy))
        for observation in self.observations:
            self.by_resource[observation.resource_id].append(observation)
            for identifier in sorted(observation.identifiers):
                self.by_identifier[identifier].append(observation)
        for coverage in self.coverage:
            self.coverage_by_system[coverage.system_id].append(coverage)


def eligible(item: Observation | SnapshotCoverage, audit_at: datetime) -> bool:
    return item.captured_at <= audit_at


def parse_file(file_id: str, captured_at: datetime, path: Path) -> tuple[list[Observation], list[SnapshotCoverage]]:
    suffix = path.suffix
    if suffix == ".sql":
        return parse_sql(file_id, captured_at, path.read_text(encoding="utf-8"))
    if suffix == ".json":
        return parse_json(file_id, captured_at, path.read_text(encoding="utf-8"))
    if suffix == ".log":
        return parse_log(file_id, captured_at, path.read_text(encoding="utf-8")), []
    if suffix == ".txt":
        return parse_text(file_id, captured_at, path.read_text(encoding="utf-8")), []
    if suffix == ".pdf":
        return parse_pdf(file_id, captured_at, pdf_text(path)), []
    raise ValueError(f"no parser for {path.name}")


def cached_parse(file_id: str, captured_at: datetime, path: Path, use_cache: bool):
    digest = hashlib.sha256(path.read_bytes() + f"|{PARSER_VERSION}|{file_id}|{captured_at.isoformat()}".encode())
    cache_path = CACHE_DIR / f"{digest.hexdigest()}.json"
    if use_cache and cache_path.is_file():
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
        return ([Observation.model_validate(o) for o in payload["observations"]],
                [SnapshotCoverage.model_validate(c) for c in payload["coverage"]])
    observations, coverage = parse_file(file_id, captured_at, path)
    if use_cache:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps({"observations": [o.model_dump(mode="json") for o in observations],
                                          "coverage": [c.model_dump(mode="json") for c in coverage]},
                                         sort_keys=True), encoding="utf-8")
    return observations, coverage


def activity_observation(activity: Activity) -> Observation:
    """State-check activity (contract §3.2): claims about current state, used only when no file establishes it."""
    from ghostaudit.evidence.derive import make_observation
    details = activity.details.lower()
    fields: dict[str, str | None] = {"event_type": activity.event_type, "reported_result": activity.reported_result,
                                     "details": activity.details}
    if activity.event_type == "CHECK_DATA_FLOW":
        fields["enabled"] = "true" if "remains enabled" in details else None
        fields["record_type"] = "DATA_FLOW"
    else:
        fields["restore_allowed"] = "true" if "can still be restored" in details else None
        fields["record_type"] = "BACKUP_ARCHIVE"
    return make_observation(evidence_id=activity.activity_id, captured_at=activity.event_time,
                            source_kind="activity", container=activity.event_type, physical_copy="activity",
                            resource_id=activity.resource_id, fields=fields, observed_at=activity.event_time,
                            system_id=activity.target_system)


def build_ledger(dataset: Dataset, use_cache: bool = True, extra: list[Observation] | None = None) -> Ledger:
    ledger = Ledger()
    extra = list(extra or [])
    png_with_records = {o.evidence_id for o in extra if o.source_kind == "png"}
    for file_id, evidence_file in sorted(dataset.evidence.items()):
        path = dataset.evidence_path(file_id)
        if path.suffix == ".png":
            if file_id not in png_with_records:
                ledger.empty_files[file_id] = "png: no vision records (not extracted, or no resource id on screen)"
            continue
        observations, coverage = cached_parse(file_id, evidence_file.captured_at, path, use_cache)
        if not observations and not coverage:
            ledger.empty_files[file_id] = "no record names a resource_id"
        ledger.add(observations, coverage)
    ledger.add([activity_observation(a) for a in dataset.activity if a.event_type in STATE_CHECK_EVENT_TYPES
                and a.reported_result == "SUCCESS"], [])
    ledger.add(extra, [])
    ledger.build_indexes()
    return ledger


CLAIM_FIELDS = {"DELETE_RECORD": {"status_code": "404"}, "ANONYMIZE_RECORD": {"result": "ANONYMIZED"},
                "REDACT_RECORD": {"result": "REDACTED"}, "DISABLE_DATA_FLOW": {"enabled": "false"},
                "BLOCK_RESTORE": {"restore_allowed": "false"}}


def trusted_claim_observations(dataset: Dataset) -> list[Observation]:
    """Evaluation-only 'trust-claims' ablation: SUCCESS operational claims treated as if they were observations."""
    from ghostaudit.evidence.derive import make_observation
    return [make_observation(evidence_id=a.activity_id, captured_at=a.event_time, source_kind="txt",
                             container="activity_claim", physical_copy="claim", resource_id=a.resource_id,
                             fields={"event_type": a.event_type, **CLAIM_FIELDS[a.event_type]},
                             observed_at=a.event_time, system_id=a.target_system)
            for a in dataset.activity if a.event_type in CLAIM_FIELDS and a.reported_result == "SUCCESS"]
