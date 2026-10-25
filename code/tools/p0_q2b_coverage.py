"""Q2b: which full-snapshot file does gold cite to prove an account ABSENT when no file mentions it?
Lists every eligible snapshot covering account_service (tables/collections, physical copies, row count)
for the 4 omission citations, plus the account's last deletion activity time (<= audit_at)."""
import json
import re
import sqlite3

from p0_common import DS, gold, read_csv, ts

man = {m["file_id"]: m for m in read_csv("evidence_files.csv")}
act = read_csv("system_activity.csv")
req = {r["case_id"]: r for r in read_csv("sample_deletion_requests.csv")}
ACCOUNT_TABLE = re.compile(r"^customer_profiles(_\w+)?$")


def account_coverage(fid):
    """-> list of (container, physical_copy, n_rows) for account_service coverage in the file."""
    p = DS / man[fid]["file_path"]
    out = []
    if p.suffix == ".sql":
        c = sqlite3.connect(":memory:")
        c.executescript(p.read_text(encoding="utf-8"))
        tabs = [r[0] for r in c.execute("select name from sqlite_master where type='table'")]
        for t in tabs:
            if ACCOUNT_TABLE.match(t):
                out.append((t, t.removeprefix("customer_profiles").lstrip("_") or "primary",
                            c.execute(f'select count(*) from "{t}"').fetchone()[0]))
            elif t.startswith("customer_data_"):  # generic store: rows carry collection_name
                n = c.execute(f'select count(*) from "{t}" where collection_name=\'customer_profiles\'').fetchone()[0]
                out.append((t + ":customer_profiles", t.removeprefix("customer_data_"), n))
    elif p.suffix == ".json":
        d = json.loads(p.read_text(encoding="utf-8"))
        for s in d.get("snapshots", []):
            if s.get("data_store") == "account_service":
                out.append((s["collection"], "bundle", len(s["records"])))
    return out


for cid, (st, steps) in sorted(gold().items()):
    cut = ts(req[cid]["audit_at"])
    for s in steps:
        if s["operation"] != "VERIFY_RECORD_ABSENT" or s["system_id"] != "account_service" or not s["evidence_id"]:
            continue
        rid = s["resource_id"]
        dels = [a["event_time"] for a in act if a["resource_id"] == rid and a["event_type"] == "DELETE_RECORD" and ts(a["event_time"]) <= cut]
        rows = []
        for f, m in man.items():
            if ts(m["captured_at"]) > cut or m["file_path"].endswith((".png", ".pdf", ".log", ".txt")):
                continue
            cov = account_coverage(f)
            if cov:
                rows.append((m["captured_at"], f, cov))
        rows.sort()
        print(f"{cid} {st} {rid} cite={s['evidence_id']} audit={req[cid]['audit_at']} last_delete={dels[-1] if dels else None}")
        for r in rows[-4:]:
            print("    ", "*" if r[1] == s["evidence_id"] else " ", r[0], r[1], r[2])
