"""SQLite snapshot exports → Observations (one per row) and SnapshotCoverage (one per table/collection)."""
from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime

from ghostaudit.evidence.derive import config, flatten, make_observation, system_for_resource
from ghostaudit.evidence.model import Observation, SnapshotCoverage
from ghostaudit.loaders import parse_ts

CAPTURED_AT_COMMENT_RE = re.compile(r"^-- (?:Captured at|snapshot_completed_at)[:=]\s*(\S+)", re.M)
GENERIC_PREFIX = "customer_data_"


def optional_ts(value: str | None) -> datetime | None:
    try:
        return parse_ts(value) if value else None
    except ValueError:
        return None


def split_table(table: str) -> tuple[str, str]:
    """customer_profiles_failover_replica → (customer_profiles, failover_replica); bare names are primary."""
    for copy in ("failover_replica", "read_replica", "reporting_replica", "primary"):
        if table.endswith("_" + copy):
            return table.removesuffix("_" + copy), copy
    return table, "primary"


def parse_sql(file_id: str, captured_at: datetime, text: str) -> tuple[list[Observation], list[SnapshotCoverage]]:
    connection = sqlite3.connect(":memory:")
    connection.executescript(text)
    match = CAPTURED_AT_COMMENT_RE.search(text)
    snapshot_at = optional_ts(match.group(1)) if match else None
    tables = sorted(t for (t,) in connection.execute("select name from sqlite_master where type='table'"))
    scope = sorted(row[0] for row in connection.execute("select origin_system from snapshot_scope")) \
        if "snapshot_scope" in tables else None
    observations: list[Observation] = []
    coverage: list[SnapshotCoverage] = []
    for table in tables:
        if table == "snapshot_scope":
            continue
        cursor = connection.execute(f'select * from "{table}"')
        columns = [d[0] for d in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        if table.startswith(GENERIC_PREFIX):
            physical_copy = table.removeprefix(GENERIC_PREFIX)
            ids_by_collection: dict[tuple[str, str], set[str]] = {}
            for row in rows:
                record = json.loads(row["record_json"])
                fields = flatten({**{k: v for k, v in row.items() if k != "record_json"}, **record})
                ids_by_collection.setdefault((row["origin_system"], row["collection_name"]), set()).add(
                    row["resource_id"])
                observations.append(make_observation(
                    evidence_id=file_id, captured_at=captured_at, source_kind="sql",
                    container=row["collection_name"], physical_copy=physical_copy, resource_id=row["resource_id"],
                    fields=fields, observed_at=optional_ts(row.get("updated_at")), system_id=row["origin_system"]))
            known = {(origin, collection) for origin, collections in config()["generic_store_collections"].items()
                     for collection in collections}
            for origin, collection in sorted(known | set(ids_by_collection)):
                ids = ids_by_collection.get((origin, collection), set())
                coverage.append(SnapshotCoverage(
                    file_id=file_id, captured_at=captured_at, snapshot_at=snapshot_at, system_id=origin,
                    collection=collection, physical_copy=physical_copy, scope="full_table", row_count=len(ids),
                    resource_ids=frozenset(ids)))
            continue
        container, physical_copy = split_table(table)
        for row in rows:
            observations.append(make_observation(
                evidence_id=file_id, captured_at=captured_at, source_kind="sql", container=container,
                physical_copy=physical_copy, resource_id=row["resource_id"], fields=flatten(row),
                observed_at=optional_ts(row.get("updated_at") or row.get("indexed_at"))))
        if scope is not None:
            system_id = config()["inventory_table_system"].get(table)
            if system_id not in scope:
                continue                        # inventory table outside snapshot_scope: no coverage claim
            scope_label = ",".join(scope)
        else:
            system_id = system_for_resource(rows[0]["resource_id"]) if rows else \
                {"customer_profiles": "account_service", "search_documents": "search_service"}.get(container)
            scope_label = "full_table"
        if system_id is None:
            continue
        coverage.append(SnapshotCoverage(
            file_id=file_id, captured_at=captured_at, snapshot_at=snapshot_at, system_id=system_id,
            collection=container, physical_copy=physical_copy, scope=scope_label, row_count=len(rows),
            resource_ids=frozenset(row["resource_id"] for row in rows)))
    return observations, coverage
