"""Q2: which file does gold cite when several eligible files mention a resource?

Hypotheses tested per cited gold step:
  H_latest: cite == latest file (by manifest captured_at) <= audit_at mentioning the resource_id
  H_file_cutoff: no cited file has captured_at > audit_at
"""
from collections import Counter

from p0_common import gold, load_text, read_csv, ts

text = load_text()
man = {m["file_id"]: m for m in read_csv("evidence_files.csv")}
req = {r["case_id"]: r for r in read_csv("sample_deletion_requests.csv")}
stats = Counter()
misses = []
for cid, (status, steps) in sorted(gold().items()):
    cut = ts(req[cid]["audit_at"])
    for s in steps:
        ev = s["evidence_id"]
        if not ev:
            continue
        stats["cited"] += 1
        if ts(man[ev]["captured_at"]) > cut:
            stats["cite_after_audit"] += 1
        rid = s["resource_id"]
        cands = sorted(
            (ts(man[f]["captured_at"]), f) for f, t in text.items()
            if rid in t and ts(man[f]["captured_at"]) <= cut
        )
        if rid not in text.get(ev, "") and man[ev]["file_path"].endswith(".png"):
            stats["cite_is_png"] += 1
        if not cands:
            stats["no_text_candidate"] += 1
            misses.append((cid, s["operation"], rid, ev, "no-text-cand", man[ev]["file_path"]))
            continue
        if cands[-1][1] == ev:
            stats["latest_match"] += 1
        else:
            stats["latest_mismatch"] += 1
            misses.append((cid, s["operation"], rid, ev, [f for _, f in cands][-3:], status))
print(dict(stats))
for m in misses:
    print(m)
