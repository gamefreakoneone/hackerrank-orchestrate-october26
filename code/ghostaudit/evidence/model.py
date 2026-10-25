"""Evidence ledger contracts (TECHNICAL_DESIGN §3.2, §3.3)."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from ghostaudit.models import Frozen

SourceKind = Literal["sql", "json", "log", "txt", "pdf", "png", "activity"]


class Observation(Frozen):
    evidence_id: str                  # file_id; activity_id when source_kind == "activity"
    captured_at: datetime             # manifest captured_at (activity event_time) — the cutoff key
    observed_at: datetime | None      # record-level time if present
    source_kind: SourceKind
    container: str                    # table / collection / log service / document type
    physical_copy: str                # "primary", "failover_replica", ...
    system_id: str | None
    resource_id: str
    category: str | None
    identifiers: frozenset[str]       # raw identifier values found in the record
    fields: dict[str, str | None]     # normalized record fields (None = null)


class SnapshotCoverage(Frozen):
    file_id: str
    captured_at: datetime
    snapshot_at: datetime | None
    system_id: str
    collection: str
    physical_copy: str
    scope: str
    row_count: int
    resource_ids: frozenset[str]
    covered_subjects: frozenset[str] | None = None   # records-assurance bundle: the user_ids it was exported for;
                                                     # None = not limited to particular subjects (full table)
