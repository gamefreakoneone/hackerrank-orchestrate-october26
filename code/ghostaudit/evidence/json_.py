"""JSON evidence → Observations (outermost dict carrying a resource_id) and bundle SnapshotCoverage."""
from __future__ import annotations

import json
from datetime import datetime

from ghostaudit.evidence.derive import flatten, is_resource_id, make_observation
from ghostaudit.evidence.model import Observation, SnapshotCoverage
from ghostaudit.evidence.sql import optional_ts
from ghostaudit.identity import USER_ID_RE

CONTEXT_KEYS = ("collection", "data_store", "captured_at", "observed_at", "origin", "source")


def record_time(record: dict) -> datetime | None:
    return optional_ts(record.get("observed_at") or record.get("recorded_at"))


def dated_after_snapshot(record: dict, snapshot: dict) -> bool:
    record_at, snapshot_at = record_time(record), optional_ts(snapshot.get("captured_at"))
    return record_at is not None and snapshot_at is not None and record_at > snapshot_at


def parse_json(file_id: str, captured_at: datetime, text: str) -> tuple[list[Observation], list[SnapshotCoverage]]:
    document = json.loads(text)
    observations: list[Observation] = []
    coverage: list[SnapshotCoverage] = []

    def walk(node, context: dict, path: tuple[str, ...]) -> None:
        if isinstance(node, list):
            for item in node:
                walk(item, context, path)
            return
        if not isinstance(node, dict):
            return
        if is_resource_id(node.get("resource_id")):
            fields = flatten(node)
            system_id = node.get("system") or context.get("service") or context.get("data_store")
            container = context.get("collection") or (path[-1] if path else "records")
            observed = record_time(node) or optional_ts(context.get("captured_at"))
            observations.append(make_observation(
                evidence_id=file_id, captured_at=captured_at, source_kind="json", container=container,
                physical_copy=context.get("physical_copy", "export"), resource_id=node["resource_id"],
                fields=fields, observed_at=observed, system_id=system_id))
            return
        context = {**context, **{k: node[k] for k in CONTEXT_KEYS if isinstance(node.get(k), str)}}
        if "snapshots" in node:                                   # records-assurance snapshot bundle
            # a bundle is exported for a batch of subjects: its collections are complete only for those user_ids;
            # a record dated after its snapshot was not part of it and names no covered subject (spec 0022)
            covered_subjects = frozenset(value for snapshot in node["snapshots"] for record in snapshot["records"]
                                         if not dated_after_snapshot(record, snapshot)
                                         for value in record.values()
                                         if isinstance(value, str) and USER_ID_RE.match(value))
            for snapshot in node["snapshots"]:
                records = snapshot.get("records", [])
                coverage.append(SnapshotCoverage(
                    file_id=file_id, captured_at=captured_at, snapshot_at=optional_ts(snapshot.get("captured_at")),
                    system_id=snapshot["data_store"], collection=snapshot["collection"], physical_copy="bundle",
                    scope="bundle_subjects", row_count=len(records),
                    resource_ids=frozenset(r["resource_id"] for r in records), covered_subjects=covered_subjects))
                walk(records, {**context, "data_store": snapshot["data_store"], "collection": snapshot["collection"],
                               "captured_at": snapshot.get("captured_at"), "physical_copy": "bundle"},
                     path + ("snapshots",))
            return
        for key, value in node.items():
            if key == "service_exports" and isinstance(value, dict):
                for service, collections in value.items():
                    for collection, items in collections.items():
                        walk(items, {**context, "service": service, "collection": collection},
                             path + (service, collection))
            elif isinstance(value, (dict, list)):
                walk(value, context, path + (key,))

    walk(document, {}, ())
    return observations, coverage
