"""Q2b (phase 0c): which snapshot proves an account ABSENT when no eligible file mentions it?

Builds SnapshotCoverage-like rows for account_service (table/collection, physical copy, row count, resource ids),
then scores candidate selection rules against the sample citations whose cited file does not mention the account.
Every rule is executed and asserted per case; nothing is truncated.

Candidates for a case: eligible files (captured_at <= audit_at) with account_service coverage that does NOT
contain the account. "after_delete" = captured after the account's last DELETE_RECORD activity <= audit_at.
"""
import json
import re
import sqlite3

from p0_common import DS, gold, load_text, read_csv, ts

man = {m["file_id"]: m for m in read_csv("evidence_files.csv")}
act = read_csv("system_activity.csv")
req = {r["case_id"]: r for r in read_csv("sample_deletion_requests.csv")}
ACCOUNT_TABLE = re.compile(r"^customer_profiles(_\w+)?$")


def account_coverage(fid):
    """-> list of (container, physical_copy, row_ids) for account_service coverage in the file."""
    p = DS / man[fid]["file_path"]
    out = []
    if p.suffix == ".sql":
        c = sqlite3.connect(":memory:")
        c.executescript(p.read_text(encoding="utf-8"))
        for (t,) in c.execute("select name from sqlite_master where type='table'").fetchall():
            if ACCOUNT_TABLE.match(t):
                ids = {r[0] for r in c.execute(f'select resource_id from "{t}"')}
                out.append((t, t.removeprefix("customer_profiles").lstrip("_") or "primary", ids))
            elif t.startswith("customer_data_"):  # generic store: rows carry collection_name
                ids = {r[0] for r in c.execute(f'select resource_id from "{t}" where collection_name=\'customer_profiles\'')}
                out.append((t + ":customer_profiles", t.removeprefix("customer_data_"), ids))
    elif p.suffix == ".json":
        d = json.loads(p.read_text(encoding="utf-8"))
        for s in d.get("snapshots", []):
            if s.get("data_store") == "account_service":
                out.append((s["collection"], "bundle", {r.get("resource_id") for r in s["records"]}))
    return out


def candidates(cid, rid):
    cut = ts(req[cid]["audit_at"])
    dels = [ts(a["event_time"]) for a in act if a["resource_id"] == rid and a["event_type"] == "DELETE_RECORD"
            and ts(a["event_time"]) <= cut]
    out = []
    for f, m in man.items():
        cap = ts(m["captured_at"])
        if cap > cut or not m["file_path"].endswith((".sql", ".json")):
            continue
        cov = account_coverage(f)
        if cov and not any(rid in ids for _, _, ids in cov):
            out.append({"file": f, "captured": cap, "copies": len({c for _, c, _ in cov}),
                        "has_replica": any(c not in ("primary", "bundle") for _, c, _ in cov),
                        "after_delete": not dels or cap > max(dels)})
    return out


RULES = {
    "latest": lambda cs: max(cs, key=lambda c: c["captured"]),
    "latest_after_delete": lambda cs: max([c for c in cs if c["after_delete"]] or cs, key=lambda c: c["captured"]),
    "after_delete_most_copies_then_latest (0b claim)":
        lambda cs: max([c for c in cs if c["after_delete"]] or cs, key=lambda c: (c["copies"], c["captured"])),
    "after_delete_latest_with_replica_else_latest":
        lambda cs: max([c for c in cs if c["after_delete"] and c["has_replica"]]
                       or [c for c in cs if c["after_delete"]] or cs, key=lambda c: c["captured"]),
}

if __name__ == "__main__":
    text = load_text()
    targets = [(cid, s["resource_id"], s["evidence_id"]) for cid, (_, steps) in sorted(gold().items()) for s in steps
               if s["operation"] == "VERIFY_RECORD_ABSENT" and s["system_id"] == "account_service"
               and s["evidence_id"] and s["resource_id"] not in text[s["evidence_id"]]]
    print("omission citations:", [(c, r, e) for c, r, e in targets])
    for name, rule in RULES.items():
        picks = [(cid, rule(candidates(cid, rid))["file"], cite) for cid, rid, cite in targets]
        ok = sum(p == c for _, p, c in picks)
        print(f"{ok}/{len(targets)}  {name}:", ", ".join(f"{cid}->{p}{'' if p == c else ' (gold ' + c + ')'}"
                                                       for cid, p, c in picks))
    # executable assertion for the rule adopted in TECHNICAL_DESIGN §5 Q2 (chosen post hoc among the rules above,
    # on only 4 citations: a regression check, not evidence of generality)
    CHOSEN = "after_delete_latest_with_replica_else_latest"
    got = [RULES[CHOSEN](candidates(c, r))["file"] for c, r, _ in targets]
    assert got == [e for _, _, e in targets], (CHOSEN, got)
    print(f"chosen rule {CHOSEN!r} reproduces {len(targets)}/{len(targets)} (post hoc; 4 data points)")
