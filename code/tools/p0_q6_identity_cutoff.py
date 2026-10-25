"""Q6 (phase 0c): does reading post-cutoff audit rows (to revert later identity changes) change any answer?

Compares identity_at(mode="strict") with mode="revert" for every request (samples + evaluation set) and,
for samples, the discovered resource sets. Also counts subjects whose snapshot updated_at is after audit_at.
"""
import p0_q3_discovery as d
from p0_common import read_csv, ts

reqs = read_csv("sample_deletion_requests.csv") + read_csv("deletion_requests.csv")
n = post_rows = snap_after = id_diff = 0
for r in reqs:
    cut = ts(r["audit_at"])
    d.MODE = "strict"
    uid, _ = d.subject(r["email"], cut)
    if uid is None:
        continue
    n += 1
    post_rows += any(a["user_id"] == uid and ts(a["event_time"]) > cut for a in d.audit)
    snap_after += ts(d.ids[uid]["updated_at"]) > cut
    id_diff += d.identity_at(uid, cut, "strict") != d.identity_at(uid, cut, "revert")
print(f"requests resolved: {n}; subject has audit rows after audit_at: {post_rows}; "
      f"snapshot updated_at > audit_at: {snap_after}; identifier sets differ strict vs revert: {id_diff}")
diff = []
for r in read_csv("sample_deletion_requests.csv"):
    d.MODE = "strict"; a = set(d.discover(r)[2])
    d.MODE = "revert"; b = set(d.discover(r)[2])
    if a != b:
        diff.append((r["case_id"], sorted(a ^ b)))
d.MODE = "strict"
print("sample cases whose discovered resources differ:", diff or "none")
