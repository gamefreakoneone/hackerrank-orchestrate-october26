"""Subject identity as of a request's audit_at (spec 0006). Post-cutoff audit rows and snapshots are never read."""
from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, field

from ghostaudit.loaders import Dataset
from ghostaudit.models import Request

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
HASH_RE = re.compile(r"^[0-9a-fA-F]{64}$")
USER_ID_RE = re.compile(r"^user_\d+$")
PHONE_RE = re.compile(r"^\+?[\d\s().-]{7,}$")


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_email(value: str) -> str:
    return value.strip().lower()


def normalize_phone(value: str) -> str:
    return re.sub(r"\D", "", value)


def normalize_name(value: str) -> str:
    return unicodedata.normalize("NFC", value.strip())


def identifier_kind(value: str) -> str | None:
    """email | email_hash | user_id | phone | None (names are matched by type-specific callers only)."""
    value = value.strip()
    if EMAIL_RE.match(value):
        return "email"
    if HASH_RE.match(value):
        return "email_hash"
    if USER_ID_RE.match(value):
        return "user_id"
    if PHONE_RE.match(value) and len(normalize_phone(value)) >= 7:
        return "phone"
    return None


@dataclass(frozen=True)
class Subject:
    request_email: str
    user_id: str | None
    emails: frozenset[str]            # normalized (lower-case)
    phones: frozenset[str]            # digits only
    names: frozenset[str]             # NFC
    email_hashes: frozenset[str]      # lower-case hex
    current_emails: frozenset[str]    # values from the eligible current snapshot
    flags: tuple[str, ...] = field(default=())

    @property
    def historical_emails(self) -> frozenset[str]:
        return self.emails - self.current_emails

    def matches(self, value: str, kind: str | None = None) -> bool:
        """Exact per-type equality; never substring (decoys: 'Jonas Berglund' vs 'Jonas Berg')."""
        kind = kind or identifier_kind(value)
        if kind == "email":
            return normalize_email(value) in self.emails
        if kind == "email_hash":
            return value.strip().lower() in self.email_hashes
        if kind == "user_id":
            return self.user_id is not None and value.strip() == self.user_id
        if kind == "phone":
            return normalize_phone(value) in self.phones
        if kind == "name":
            return normalize_name(value) in self.names
        return False

    def key_values(self) -> frozenset[str]:
        """Normalized identifier values for index lookups."""
        user_ids = {self.user_id} if self.user_id else set()
        return self.emails | self.phones | self.names | self.email_hashes | frozenset(user_ids)


def identifier_owner_index(dataset: Dataset, audit_at, include_audit: bool = True) -> dict[str, set[str]]:
    """Normalized identifier (email, phone, email hash, user id) -> user_ids, from values eligible at the cutoff:
    snapshots with updated_at <= audit_at and audit rows with event_time <= audit_at (later rows never read)."""
    owners: dict[str, set[str]] = {}

    def add(value: str, kind: str, user_id: str) -> None:
        if not value:
            return
        key = {"email": normalize_email, "phone": normalize_phone}.get(kind, lambda v: v.strip().lower())(value)
        owners.setdefault(key, set()).add(user_id)
        if kind == "email":
            owners.setdefault(sha256_hex(key), set()).add(user_id)

    for identity in dataset.identities.values():
        owners.setdefault(identity.user_id, set()).add(identity.user_id)
        if identity.updated_at <= audit_at:
            add(identity.email, "email", identity.user_id)
            add(identity.phone, "phone", identity.user_id)
            add(identity.email_hash, "email_hash", identity.user_id)
    for event in dataset.audit if include_audit else []:
        if event.event_time > audit_at:
            break                              # audit is sorted by event_time: later rows are never read
        for value in (event.old_value, event.new_value):
            add(value, event.field_name, event.user_id)
    return owners


def eligible_email_owner(dataset: Dataset, email: str, audit_at, include_audit: bool = True) -> str | None:
    owners = identifier_owner_index(dataset, audit_at, include_audit).get(normalize_email(email), set())
    if len(owners) > 1:
        raise ValueError(f"email maps to several users at the cutoff: {sorted(owners)}")
    return next(iter(owners), None)


def resolve(request: Request, dataset: Dataset, use_history: bool = True) -> Subject:
    """use_history=False is the evaluation-only 'no-history' ablation: audit-log values are ignored."""
    audit_at = request.audit_at
    user_id = eligible_email_owner(dataset, request.email, audit_at, include_audit=use_history)
    emails, phones, names, hashes, current_emails = set(), set(), set(), set(), set()
    flags: list[str] = []
    emails.add(normalize_email(request.email))
    if user_id is not None:
        identity = dataset.identities.get(user_id)
        if identity is not None and identity.updated_at <= audit_at:
            current_emails.add(normalize_email(identity.email))
            emails.add(normalize_email(identity.email))
            phones.add(normalize_phone(identity.phone))
            names.add(normalize_name(identity.name))
            hashes.add(identity.email_hash.lower())
        elif identity is not None:
            flags.append("IDENTITY_SNAPSHOT_AFTER_CUTOFF")
        for event in dataset.audit if use_history else []:
            if event.event_time > audit_at:
                break
            if event.user_id != user_id:
                continue
            for value in (event.old_value, event.new_value):
                if not value:
                    continue
                if event.field_name == "email":
                    emails.add(normalize_email(value))
                elif event.field_name == "phone":
                    phones.add(normalize_phone(value))
                elif event.field_name == "email_hash":
                    hashes.add(value.strip().lower())
    hashes |= {sha256_hex(email) for email in emails}
    return Subject(request_email=request.email, user_id=user_id, emails=frozenset(emails),
                   phones=frozenset(p for p in phones if p), names=frozenset(names), email_hashes=frozenset(hashes),
                   current_emails=frozenset(current_emails), flags=tuple(flags))
