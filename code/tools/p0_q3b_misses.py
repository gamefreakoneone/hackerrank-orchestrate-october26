"""Q3b: for gold resources not linked by identifiers, show their activity rows and file mentions,
and the gap between each gold resource's activity and the case's reported_at."""
from collections import Counter

from p0_common import gold, load_text, read_csv, ts

text = load_text()
man = {m["file_id"]: m for m in read_csv("evidence_files.csv")}
act = read_csv("system_activity.csv")
req = {r["case_id"]: r for r in read_csv("sample_deletion_requests.csv")}
MISSES = {"case_02": ["account_002"], "case_04": ["account_004"], "case_08": ["account_008"],
          "case_09": ["audit_record_4902"], "case_10": ["account_010", "support_002"],
          "case_15": ["audit_record_1596", "data_flow_9846"], "case_17": ["backup_3245"],
          "case_18": ["audit_record_6645"], "case_23": ["audit_record_4128"], "case_30": ["audit_record_1707"]}
for cid, rids in MISSES.items():
    r = req[cid]
    print(f"== {cid} req={r['requested_at']} rep={r['reported_at']} audit={r['audit_at']}")
    for rid in rids:
        for a in act:
            if a["resource_id"] == rid or rid in a["details"]:
                print("  ACT", a["activity_id"], a["event_time"], a["event_type"], a["reported_result"], a["details"][:110])
        for f, t in text.items():
            if rid in t:
                i = t.index(rid)
                print("  FILE", f, man[f]["captured_at"], "BEFORE" if ts(man[f]["captured_at"]) <= ts(r["audit_at"]) else "AFTER",
                      repr(t[max(0, i - 120):i + 80].replace("\n", " | ")))
# gap stats: for every gold resource, min |event_time - reported_at| over its activity rows
gaps = Counter()
for cid, (_, steps) in gold().items():
    rep = ts(req[cid]["reported_at"])
    for s in steps:
        if s["phase"] != "VERIFICATION" and gold()[cid][0] == "INCOMPLETE":
            continue
        d = [abs((ts(a["event_time"]) - rep).total_seconds()) for a in act if a["resource_id"] == s["resource_id"]]
        b = "none" if not d else "<=60s" if min(d) <= 60 else "<=1h" if min(d) <= 3600 else ">1h"
        gaps[(s["resource_id"].rsplit("_", 1)[0], b)] += 1
print(sorted(gaps.items()))
