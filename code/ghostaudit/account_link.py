"""Subject-level account linkage (spec 0010, TECHNICAL_DESIGN §5 Q3). Only grounded links name an account;
workflow-timing candidates are ranked for diagnostics and never ground the account."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Literal

from ghostaudit.discovery import Discovered
from ghostaudit.evidence.index import Ledger, eligible
from ghostaudit.identity import Subject
from ghostaudit.loaders import Dataset
from ghostaudit.models import Request

ACCOUNT_SYSTEM = "account_service"
WORKFLOW_WINDOW_AFTER_REPORT = timedelta(minutes=15)


@dataclass
class AccountLink:
    via: Literal["grounded", "multi_grounded", "ungrounded"]
    current: str | None
    historical: list[str] = field(default_factory=list)
    excluded: dict[str, str] = field(default_factory=dict)          # account -> reason
    ranked_candidates: list[str] = field(default_factory=list)      # diagnostics only
    link_times: dict[str, str] = field(default_factory=dict)

    @property
    def flags(self) -> list[str]:
        return {"ungrounded": ["ACCOUNT_UNGROUNDED"], "multi_grounded": ["ACCOUNT_MULTI_GROUNDED"]}.get(self.via, [])

    def as_dict(self) -> dict:
        return {"via": self.via, "current": self.current, "historical": self.historical, "excluded": self.excluded,
                "ranked_candidates": self.ranked_candidates, "link_times": self.link_times}


def other_owners(resource_id: str, subject: Subject, ledger: Ledger, owners: dict[str, set[str]], audit_at) -> set[str]:
    """Known users other than the subject named by any eligible record of the resource."""
    users: set[str] = set()
    for observation in ledger.by_resource.get(resource_id, []):
        if eligible(observation, audit_at):
            for identifier in observation.identifiers:
                users |= owners.get(identifier, set())
    return users - {subject.user_id}


def rank_workflow_candidates(subject: Subject, request: Request, dataset: Dataset, ledger: Ledger,
                             owners: dict[str, set[str]]) -> list[str]:
    upper = min(request.audit_at, request.reported_at + WORKFLOW_WINDOW_AFTER_REPORT)
    events = [a for a in dataset.activity if a.event_type == "DELETE_RECORD" and a.target_system == ACCOUNT_SYSTEM
              and request.requested_at <= a.event_time <= upper]
    events = [a for a in events if not other_owners(a.resource_id, subject, ledger, owners, request.audit_at)]
    events.sort(key=lambda a: (abs((a.event_time - request.reported_at).total_seconds()), a.resource_id))
    return list(dict.fromkeys(a.resource_id for a in events))


def link_account(subject: Subject, request: Request, discovered: dict[str, Discovered], dataset: Dataset,
                 ledger: Ledger, owners: dict[str, set[str]]) -> AccountLink:
    grounded = {rid: d for rid, d in discovered.items() if d.system_id == ACCOUNT_SYSTEM and d.grounded}
    excluded = {}
    for resource_id in sorted(grounded):
        others = other_owners(resource_id, subject, ledger, owners, request.audit_at)
        if others:
            excluded[resource_id] = f"linked to other user(s) {sorted(others)}"
    accounts = {rid: d for rid, d in grounded.items() if rid not in excluded}
    link_times = {rid: d.last_link_at().isoformat() for rid, d in accounts.items()}
    if not accounts:
        return AccountLink("ungrounded", None, excluded=excluded,
                           ranked_candidates=rank_workflow_candidates(subject, request, dataset, ledger, owners))
    ordered = sorted(accounts, key=lambda rid: (accounts[rid].last_link_at(), rid), reverse=True)
    via = "grounded" if len(ordered) == 1 else "multi_grounded"
    return AccountLink(via, ordered[0], historical=sorted(ordered[1:]), excluded=excluded, link_times=link_times)
