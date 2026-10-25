"""Resource discovery for one request (spec 0010): exact identifier links, LINK_RESOURCE_IDENTITY, reference edges.
Only evidence captured and observed (activity: event_time) at or before audit_at is read (spec 0022)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime

from ghostaudit.evidence.derive import RESOURCE_RE, system_for_resource
from ghostaudit.evidence.index import Ledger, eligible
from ghostaudit.evidence.model import Observation
from ghostaudit.identity import Subject, normalize_email
from ghostaudit.loaders import Dataset
from ghostaudit.models import Activity, Request

REFERENCE_FIELDS = ("source_resource_id",)
REPOPULATED_RE = re.compile(r"repopulated downstream resource (\S+?)\.?$")
MAX_EXPANSION_ROUNDS = 3


@dataclass
class Link:
    via: str                 # identifier | link_activity | reference | restore_claim
    evidence_id: str
    linked_at: datetime      # captured_at / event_time of the linking record


@dataclass
class Discovered:
    resource_id: str
    system_id: str | None
    links: list[Link] = field(default_factory=list)

    @property
    def vias(self) -> set[str]:
        return {link.via for link in self.links}

    @property
    def grounded(self) -> bool:
        """Grounded = a subject identifier and the resource in one record, a catalog link, or a reference edge from
        a grounded resource. A restore claim names a candidate but does not ground it."""
        return bool(self.vias - {"restore_claim"})

    def last_link_at(self) -> datetime:
        return max(link.linked_at for link in self.links if link.via != "restore_claim")


def subject_link_keys(subject: Subject) -> frozenset[str]:
    """Identifiers that can link a record on their own. Names never do (decoys: 'Jonas Berg' / 'Jonas Berglund')."""
    return subject.key_values() - subject.names


def link_activity_matches(activity: Activity, subject: Subject) -> bool:
    tokens = set(re.findall(r"[^\s()]+@[^\s()]+?(?=\.?(?:\s|$))|user_\d+", activity.details))
    return any((subject.user_id and token == subject.user_id) or normalize_email(token) in subject.emails
               for token in tokens)


def discover(subject: Subject, request: Request, dataset: Dataset, ledger: Ledger) -> dict[str, Discovered]:
    audit_at = request.audit_at
    found: dict[str, Discovered] = {}

    def add(resource_id: str, link: Link) -> bool:
        is_new = resource_id not in found
        entry = found.setdefault(resource_id, Discovered(resource_id, system_for_resource(resource_id)))
        if all((l.via, l.evidence_id) != (link.via, link.evidence_id) for l in entry.links):
            entry.links.append(link)
        return is_new

    for key in sorted(subject_link_keys(subject)):
        for observation in ledger.by_identifier.get(key, []):
            if eligible(observation, audit_at):
                add(observation.resource_id, Link("identifier", observation.evidence_id, observation.captured_at))
    eligible_activity = [a for a in dataset.activity if a.event_time <= audit_at]
    for activity in eligible_activity:
        if activity.event_type == "LINK_RESOURCE_IDENTITY" and link_activity_matches(activity, subject):
            add(activity.resource_id, Link("link_activity", activity.activity_id, activity.event_time))

    frontier = set(found)
    for _ in range(MAX_EXPANSION_ROUNDS):
        new: set[str] = set()
        for resource_id in sorted(frontier):
            if not found[resource_id].grounded:
                continue
            for observation in ledger.by_resource.get(resource_id, []):     # this record points at another
                for field_name in REFERENCE_FIELDS:
                    target = observation.fields.get(field_name)
                    if eligible(observation, audit_at) and target and RESOURCE_RE.fullmatch(target):
                        if add(target, Link("reference", observation.evidence_id, observation.captured_at)):
                            new.add(target)
            for observation in referencing_observations(ledger, resource_id, audit_at):   # another points here
                if add(observation.resource_id, Link("reference", observation.evidence_id, observation.captured_at)):
                    new.add(observation.resource_id)
            for activity in eligible_activity:
                if activity.event_type == "RESTORE_BACKUP" and activity.resource_id == resource_id:
                    match = REPOPULATED_RE.search(activity.details)
                    if match and add(match.group(1), Link("restore_claim", activity.activity_id, activity.event_time)):
                        new.add(match.group(1))
        if not new:
            break
        frontier = new
    return found


def referencing_observations(ledger: Ledger, resource_id: str, audit_at: datetime) -> list[Observation]:
    return [o for o in ledger.observations if eligible(o, audit_at)
            and any(o.fields.get(f) == resource_id for f in REFERENCE_FIELDS)]
