from pathlib import Path

import pytest

from ghostaudit.evidence.index import build_ledger
from ghostaudit.evidence.logs import parse_line
from ghostaudit.identity import normalize_phone
from ghostaudit.loaders import load_dataset

DATASET_DIR = Path(__file__).resolve().parents[2] / "dataset"


@pytest.fixture(scope="module")
def ledger():
    return build_ledger(load_dataset(DATASET_DIR), use_cache=False)


def observations(ledger, file_id, resource_id):
    return [o for o in ledger.by_resource[resource_id] if o.evidence_id == file_id]


def test_sql_rows_and_replica_coverage(ledger):
    (row,) = observations(ledger, "evidence_54", "account_005")
    assert row.physical_copy == "failover_replica" and row.system_id == "account_service"
    assert row.category == "USER_PROFILE"
    assert {"user_05", "leila.haddad@yahoo.com", normalize_phone("+212 6 48 27 15 93")} <= row.identifiers
    copies = {c.physical_copy for c in ledger.coverage if c.file_id == "evidence_54"}
    assert copies == {"primary", "failover_replica"}


def test_sql_generic_store_record_json_is_merged(ledger):
    rows = observations(ledger, "evidence_05", "search_1007")
    assert {r.physical_copy for r in rows} == {"primary", "read_replica"}
    row = rows[0]
    assert row.system_id == "search_service" and row.container == "customer_search_documents"
    assert row.fields["document.customer_reference"] == "user_53" and "user_53" in row.identifiers
    accounts = [c for c in ledger.coverage if c.file_id == "evidence_05" and c.collection == "customer_profiles"]
    assert {c.physical_copy for c in accounts} == {"primary", "read_replica"}


def test_inventory_coverage_respects_snapshot_scope(ledger):
    inventory = [c for c in ledger.coverage if c.file_id == "evidence_90"]
    assert [(c.system_id, c.collection, c.row_count) for c in inventory] == [("account_service", "customer_profiles", 0)]


def test_inventory_uppercase_emails_are_normalized(ledger):
    flows = [o for o in ledger.observations if o.evidence_id == "evidence_63" and o.category == "DATA_FLOW"]
    assert flows and all(i == i.lower() for o in flows for i in o.identifiers if "@" in i)
    assert flows[0].fields["enabled"] == "true"


def test_json_bundle_empty_collection_is_coverage(ledger):
    accounts = [c for c in ledger.coverage if c.file_id == "evidence_51" and c.system_id == "account_service"]
    assert len(accounts) == 1 and accounts[0].row_count == 0 and accounts[0].physical_copy == "bundle"


def test_json_service_export_lookup(ledger):
    (lookup,) = observations(ledger, "evidence_92", "account_3136")
    assert lookup.system_id == "account_service" and lookup.fields["status_code"] == "404"
    assert lookup.fields["profile"] is None and not lookup.identifiers


def test_json_history_records_carry_record_type(ledger):
    (record,) = observations(ledger, "evidence_13", "account_1084")
    assert record.category == "USER_PROFILE" and record.fields["result"] == "NOT_FOUND"
    assert "mateo.alvarez@gmail.com" in record.identifiers


def test_log_trace_group_joins_lookup_key_and_result(ledger):
    (readback,) = observations(ledger, "evidence_67", "account_6523")
    assert readback.fields["http_status"] == "404" and "leonie.g9352@outlook.com" in readback.identifiers
    assert readback.fields["events"] == "profile_lookup_started,profile_lookup_completed"


@pytest.mark.parametrize("line,service,trace_id,event", [
    ('2026-08-22T10:51:11Z <15>1 node-1 account_service tr-4973247 - - level=DEBUG event="profile_lookup_started" '
     'lookup_key="a@b.com"', "account_service", "tr-4973247", "profile_lookup_started"),
    ('2026-07-28T05:51:18Z [DEBUG] [account_service] [tr-6074163] profile_lookup_started: lookup_key="a@b.com"',
     "account_service", "tr-6074163", "profile_lookup_started"),
    ('2026-07-03T07:51:32Z | DEBUG | security_service | tr-5156005 | audit_record_read_completed | '
     'resource_id="audit_record_4413"', "security_service", "tr-5156005", "audit_record_read_completed"),
    ('2026-06-08T06:52:09Z requestId=tr-1108860 level=INFO function=search_service message="resource_id=\\"search_021\\" '
     'event=\\"index_query_completed\\""', "search_service", "tr-1108860", "index_query_completed"),
    ('2026-09-10T08:56:17Z {"service":"account_service","trace_id":"tr-5563868","event":"profile_lookup_started"}',
     "account_service", "tr-5563868", "profile_lookup_started"),
    ("2026-05-14T11:51:20Z level=INFO service=account_service trace_id=tr-4210650 event=profile_lookup_completed",
     "account_service", "tr-4210650", "profile_lookup_completed"),
])
def test_six_log_formats(line, service, trace_id, event):
    record = parse_line(line)
    assert (record["service"], record["trace_id"], record["event"]) == (service, trace_id, event)


def test_txt_handover_rows(ledger):
    (row,) = observations(ledger, "evidence_03", "data_flow_9522")
    assert row.system_id == "integration_service" and row.category == "DATA_FLOW" and row.fields["result"] == "ACTIVE"
    assert "novak.tomasz@icloud.com" in row.identifiers


def test_pdf_attachment(ledger):
    (attachment,) = observations(ledger, "evidence_58", "support_001")
    assert attachment.category == "SUPPORT_ATTACHMENT" and "priya.raman@gmail.com" in attachment.identifiers
    assert normalize_phone("+91 98765 73142") in attachment.identifiers


def test_state_check_activity_observation(ledger):
    checks = [o for o in ledger.observations if o.source_kind == "activity"]
    assert checks and all(o.evidence_id.startswith("activity_") for o in checks)
    assert {o.fields.get("enabled") or o.fields.get("restore_allowed") for o in checks} == {"true"}


def test_every_non_png_file_yields_records_or_a_reason(ledger):
    dataset = load_dataset(DATASET_DIR)
    produced = {o.evidence_id for o in ledger.observations if o.source_kind != "activity"} | \
        {c.file_id for c in ledger.coverage}
    assert set(dataset.evidence) == produced | set(ledger.empty_files)
