"""Per-request assessment: identity → discovery → account link → state → obligations (→ plan, spec 0012)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from ghostaudit.account_link import ACCOUNT_SYSTEM, AccountLink, link_account
from ghostaudit.discovery import Discovered, discover
from ghostaudit.evidence.index import Ledger, eligible
from ghostaudit.identity import Subject, identifier_owner_index, resolve
from ghostaudit.loaders import Dataset
from ghostaudit.models import Request
from ghostaudit.models import Status, Step
from ghostaudit.obligations import PolicyOutcome, build_obligation
from ghostaudit.planner import plan
from ghostaudit.policy import category_fallback, condition, required_state
from ghostaudit.timeline import delete_claim_times, last_delete_before, resource_category, state_at


@dataclass
class Context:
    dataset: Dataset
    ledger: Ledger
    llm: object | None = None                       # LLMLayer; None = no model calls (category fallback skipped)
    deletes: dict[str, list[datetime]] = field(default_factory=dict)
    _owners: dict[datetime, dict] = field(default_factory=dict)

    def __post_init__(self):
        self.deletes = delete_claim_times(self.dataset.activity)

    def owners(self, audit_at: datetime) -> dict:
        if audit_at not in self._owners:
            self._owners[audit_at] = identifier_owner_index(self.dataset, audit_at)
        return self._owners[audit_at]


@dataclass
class Assessment:
    request: Request
    subject: Subject
    discovered: dict[str, Discovered]
    account_link: AccountLink
    policy: PolicyOutcome
    categories: dict[str, str | None]
    category_sources: dict[str, str]

    @property
    def flags(self) -> list[str]:
        flags = set(self.account_link.flags) | set(self.subject.flags)
        obligations = self.policy.obligations
        if any(o.current == "UNKNOWN" for o in obligations):
            flags.add("UNKNOWN_STATE")
        if self.policy.policy_undefined:
            flags.add("POLICY_UNDEFINED")
        if self.policy.condition_defaulted:
            flags.add("CONDITION_DEFAULTED")
        if not obligations:
            flags.add("EMPTY_OBLIGATIONS")
        if any(o.proof_kind == "activity" for o in obligations):
            flags.add("ACTIVITY_CITATION")
        return sorted(flags)


def assess(request: Request, ctx: Context) -> Assessment:
    dataset, ledger, audit_at = ctx.dataset, ctx.ledger, request.audit_at
    subject = resolve(request, dataset)
    discovered = discover(subject, request, dataset, ledger)
    link = link_account(subject, request, discovered, dataset, ledger, ctx.owners(audit_at))
    outcome = PolicyOutcome()
    categories: dict[str, str | None] = {}
    sources: dict[str, str] = {}
    targets: list[tuple[str, str | None]] = []
    if link.via != "ungrounded":
        targets += [(account, ACCOUNT_SYSTEM) for account in [link.current, *link.historical]]
    targets += [(rid, d.system_id) for rid, d in sorted(discovered.items())
                if d.system_id != ACCOUNT_SYSTEM and d.grounded]
    for resource_id, system_id in targets:
        category = resource_category(resource_id, audit_at, ledger)
        sources[resource_id] = "record"
        if category is None and ctx.llm is not None:
            category = category_fallback(ctx.llm, resource_id, system_id, dataset.rules)
            sources[resource_id] = "jev_fallback"
        categories[resource_id] = category
        rule = dataset.rules.get(category or "")
        required = required_state(category or "", rule)
        if required is None or system_id is None:
            outcome.excluded[resource_id] = f"no applicable rule for category {category}"
            continue
        observations = [o for o in ledger.by_resource.get(resource_id, []) if eligible(o, audit_at)]
        rule_condition = condition(category, rule, observations, audit_at)
        if rule_condition == "FALSE":
            outcome.policy_undefined.append(resource_id)
            continue
        if rule_condition == "UNKNOWN":
            outcome.condition_defaulted.append(resource_id)
        state = state_at(resource_id, system_id, category, audit_at, ledger,
                         last_delete_before(ctx.deletes, resource_id, audit_at))
        outcome.obligations.append(build_obligation(system_id=system_id, resource_id=resource_id, category=category,
                                                    required=required, condition=rule_condition, state=state,
                                                    subject=subject))
    return Assessment(request, subject, discovered, link, outcome, categories, sources)


def diagnostics_record(assessment: Assessment, status: Status, steps: list[Step]) -> dict:
    return {
        "case_id": assessment.request.case_id,
        "status": status.value,
        "flags": assessment.flags,
        "intent": {"label": "DELETION", "source": "not evaluated before spec 0013"},
        "subject": {"user_id": assessment.subject.user_id,
                    "historical_request_email": assessment.request.email.strip().lower()
                    in assessment.subject.historical_emails},
        "account_link": assessment.account_link.as_dict(),
        "discovered": {rid: sorted(d.vias) for rid, d in sorted(assessment.discovered.items())},
        "categories": {rid: [c, assessment.category_sources.get(rid)] for rid, c in sorted(assessment.categories.items())},
        "obligations": [o.model_dump(mode="json") for o in assessment.policy.obligations],
        "excluded": assessment.policy.excluded,
        "policy_undefined": assessment.policy.policy_undefined,
        "condition_defaulted": assessment.policy.condition_defaulted,
        "step_count": len(steps),
    }


def run_case(request: Request, ctx: Context) -> tuple[Status, list[Step], dict]:
    assessment = assess(request, ctx)
    status, steps = plan(assessment.policy.obligations, assessment.flags)
    return status, steps, diagnostics_record(assessment, status, steps)
