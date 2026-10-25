"""Q3c: can the subject's account_service resource be chosen from deletion-window activity
by excluding candidates that evidence links to a different user?"""
import re
from collections import Counter, defaultdict
from datetime import timedelta

from p0_q3_discovery import RECS, act, gold, ids, read_csv, subject, ts

email2u = {u["email"]: k for k, u in ids.items()}
for a in read_csv("user_audit_log.csv"):
    if a["field_name"] == "email":
        email2u[a["old_value"]] = email2u[a["new_value"]] = a["user_id"]
UID_RE = re.compile(r"\buser_\d+\b")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
owner = defaultdict(set)  # resource -> users it is linked to anywhere
for f, recs in RECS.items():
    for rec in recs:
        us = set(UID_RE.findall(rec)) | {email2u[e] for e in EMAIL_RE.findall(rec) if e in email2u}
        for x in set(re.findall(r"\baccount_\d+\b", rec)):
            owner[x] |= us
for a in act:
    if a["event_type"] == "LINK_RESOURCE_IDENTITY":
        owner[a["resource_id"]] |= set(UID_RE.findall(a["details"]))
req = {r["case_id"]: r for r in read_csv("sample_deletion_requests.csv")}
c = Counter()
for cid, (st, steps) in sorted(gold().items()):
    r = req[cid]
    uid, _ = subject(r["email"], ts(r["audit_at"]))
    ga = [s["resource_id"] for s in steps if s["system_id"] == "account_service"][0]
    cand = sorted({a["resource_id"] for a in act if a["event_type"] == "DELETE_RECORD" and a["target_system"] == "account_service"
                   and ts(r["requested_at"]) <= ts(a["event_time"]) <= ts(r["reported_at"]) + timedelta(minutes=15)})
    own = [x for x in cand if uid in owner[x]]
    free = [x for x in cand if not owner[x]]
    pick = own[0] if len(own) == 1 else (free[0] if len(free) == 1 and not own else None)
    k = "own_ok" if own == [ga] else "free_unique_ok" if pick == ga else "ambiguous" if pick is None else "wrong"
    c[k] += 1
    if k in ("ambiguous", "wrong"):
        print(cid, st, "gold", ga, "own", own, "free", free)
print(dict(c))
