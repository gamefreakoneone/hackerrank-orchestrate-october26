from datetime import datetime, timezone

from ghostaudit.evidence.model import Observation
from ghostaudit.models import Rule
from ghostaudit.policy import condition, required_state

AUDIT_AT = datetime(2026, 9, 15, 12, tzinfo=timezone.utc)


def rule(category, action, text="Always"):
    return Rule(rule_id="r", data_category=category, condition=text, required_action=action)


def observation(**fields):
    return Observation(evidence_id="evidence_x", captured_at=AUDIT_AT, observed_at=None, source_kind="json",
                       container="c", physical_copy="export", system_id="security_service",
                       resource_id="audit_record_1", category="SECURITY_AUDIT_LOG", identifiers=frozenset(),
                       fields=fields)


def test_required_states_from_rules():
    assert required_state("USER_PROFILE", rule("USER_PROFILE", "DELETE")) == "ABSENT"
    assert required_state("SUPPORT_MESSAGE", rule("SUPPORT_MESSAGE", "REDACT")) == "REDACTED"
    assert required_state("ANALYTICS_PROFILE", rule("ANALYTICS_PROFILE", "ANONYMIZE")) == "ANONYMIZED"
    assert required_state("SECURITY_AUDIT_LOG", rule("SECURITY_AUDIT_LOG", "RETAIN")) == "PRESENT"
    assert required_state("BACKUP_ARCHIVE", rule("BACKUP_ARCHIVE", "RETAIN")) == "BLOCKED"
    assert required_state("ACCOUNT_TOMBSTONE", rule("ACCOUNT_TOMBSTONE", "REDACT")) == "REDACTED"
    assert required_state("DATA_FLOW", None) == "DISABLED"
    assert required_state("OBJECT", None) is None


def test_retention_condition_is_tri_state():
    audit_rule = rule("SECURITY_AUDIT_LOG", "RETAIN", "Record is within the supplied retention period")
    assert condition("SECURITY_AUDIT_LOG", audit_rule, [observation(retention_until="2031-12-31T23:59:59Z")],
                     AUDIT_AT) == "TRUE"
    assert condition("SECURITY_AUDIT_LOG", audit_rule, [observation(retention_until="2026-01-01T00:00:00Z")],
                     AUDIT_AT) == "FALSE"
    assert condition("SECURITY_AUDIT_LOG", audit_rule, [observation()], AUDIT_AT) == "UNKNOWN"


def test_latest_retention_value_wins():
    audit_rule = rule("SECURITY_AUDIT_LOG", "RETAIN", "Record is within the supplied retention period")
    older = observation(retention_until="2031-12-31T23:59:59Z").model_copy(
        update={"captured_at": datetime(2026, 1, 1, tzinfo=timezone.utc)})
    newer = observation(retention_until="2026-02-01T00:00:00Z")
    assert condition("SECURITY_AUDIT_LOG", audit_rule, [older, newer], AUDIT_AT) == "FALSE"


def test_always_rules_and_tombstones():
    assert condition("USER_PROFILE", rule("USER_PROFILE", "DELETE"), [], AUDIT_AT) == "TRUE"
    tombstone_rule = rule("ACCOUNT_TOMBSTONE", "REDACT", "Account is deleted and only a stable internal user_id...")
    assert condition("ACCOUNT_TOMBSTONE", tombstone_rule, [observation(account_status="DELETED")], AUDIT_AT) == "TRUE"
    assert condition("SUPPORT_MESSAGE", rule("SUPPORT_MESSAGE", "REDACT", "Conversation contains shared context"),
                     [], AUDIT_AT) == "UNKNOWN"


def test_category_fallback_uses_jev_choice(tmp_path, monkeypatch):
    from ghostaudit.llm.cache import DiskCache
    from ghostaudit.llm.providers import LLMLayer, TransportResult
    from ghostaudit.policy import category_fallback

    monkeypatch.setenv("JEV_MODEL", "fake-jev")
    seen = {}

    def fake_jev(*, inputs, schema, images):
        seen.update(inputs)
        return TransportResult(output={"record_kind": {"choice": "ACCOUNT_TOMBSTONE", "confidence": 0.9,
                                                       "probabilities": {"ACCOUNT_TOMBSTONE": 0.9}}},
                               input_tokens=5, output_tokens=1, served_model="fake-jev")

    layer = LLMLayer(ledger_path=None, cache=DiskCache(tmp_path), transports={"jev": fake_jev})
    rules = {"ACCOUNT_TOMBSTONE": rule("ACCOUNT_TOMBSTONE", "REDACT", "Account is deleted")}
    assert category_fallback(layer, "tombstone_17", "identity_service", rules) == "ACCOUNT_TOMBSTONE"
    assert "DATA_FLOW" in seen["questions"]["record_kind"]["criteria"]
    assert layer.ledger.rows[0]["task"] == "category_fallback"
