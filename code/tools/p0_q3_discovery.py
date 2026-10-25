"""Q3: discovery recall. For each sample case, which sources surface each gold resource?

Sources (all restricted to <= audit_at):
  ID  : resource ids co-occurring with a subject identifier in one evidence record
        (SQL/log/txt line, JSON object, whole PDF)
  LNK : LINK_RESOURCE_IDENTITY activity naming a subject email/user_id
  EXP : resources co-occurring (same record) with an already-found resource (1 hop)
"""
import hashlib
import re
import json
from collections import defaultdict

from p0_common import RES_RE, gold, load_text, read_csv, ts

text = load_text()
man = {m["file_id"]: m for m in read_csv("evidence_files.csv")}
ids = {u["user_id"]: u for u in read_csv("user_identities.csv")}
audit = read_csv("user_audit_log.csv")
act = read_csv("system_activity.csv")


def records(fid):
    t = text[fid]
    p = man[fid]["file_path"]
    if p.endswith(".json"):
        out = []

        def walk(o):
            if isinstance(o, dict):
                if any(isinstance(v, str) and RES_RE.fullmatch(v) for v in o.values()):
                    out.append(json.dumps(o))
                else:
                    for v in o.values():
                        walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
        walk(json.loads(t))
        return out
    if p.endswith(".pdf"):
        return [t]
    # logs: group lines by trace_id (started line carries the lookup key, completed line the resource)
    groups, out = {}, []
    for line in t.splitlines():
        m = TRACE_RE.search(line)
        if m:
            groups.setdefault(m.group(1), []).append(line)
        else:
            out.append(line)
    return out + ["\n".join(v) for v in groups.values()]


TRACE_RE = re.compile(r'trace_id["=:\s]+"?([\w-]+)')
RECS = {f: records(f) for f in text}


def subject(email, cut):
    uid = next((u for u, r in ids.items() if r["email"] == email), None)
    if uid is None:
        uid = next(a["user_id"] for a in audit if a["field_name"] == "email" and email in (a["old_value"], a["new_value"]))
    u = ids[uid]
    vals = {uid, u["email"], u["phone"], u["name"], u["email_hash"]}
    for a in audit:
        if a["user_id"] == uid and ts(a["event_time"]) <= cut:
            vals |= {a["old_value"], a["new_value"]}
    vals |= {hashlib.sha256(v.encode()).hexdigest() for v in list(vals) if "@" in v}
    return uid, {v for v in vals if v}


def hit(rec, vals, uid):
    return any(v in rec for v in vals if v != uid) or f"'{uid}'" in rec or f'"{uid}"' in rec or f"={uid}" in rec or f" {uid} " in rec or rec.endswith(uid)


req = {r["case_id"]: r for r in read_csv("sample_deletion_requests.csv")}
tot = defaultdict(int)
for cid, (status, steps) in sorted(gold().items()):
    r = req[cid]
    cut = ts(r["audit_at"])
    uid, vals = subject(r["email"], cut)
    eligible = [f for f in text if ts(man[f]["captured_at"]) <= cut]
    src = defaultdict(set)
    for f in eligible:
        for rec in RECS[f]:
            if hit(rec, vals, uid):
                for x in RES_RE.findall(rec):
                    src[x].add("ID")
    for a in act:
        if ts(a["event_time"]) > cut:
            continue
        if a["event_type"] == "LINK_RESOURCE_IDENTITY" and any(v in a["details"] for v in vals):
            src[a["resource_id"]].add("LNK")
    found = set(src)
    for f in eligible:
        for rec in RECS[f]:
            xs = set(RES_RE.findall(rec))
            if xs & found:
                for x in xs - found:
                    src[x].add("EXP")
    g = {s["resource_id"] for s in steps}
    miss = sorted(g - set(src))
    extra = sorted(x for x in set(src) - g if src[x] != {"EXP"})
    for x in g:
        tot["gold"] += 1
        for k in src.get(x, ()):
            tot["gold_" + k] += 1
        if x in src and src[x] <= {"EXP"}:
            tot["gold_only_EXP"] += 1
    tot["miss"] += len(miss)
    tot["extra_nonEXP"] += len(extra)
    print(cid, status, "miss=", miss, "extra=", extra[:8], len(extra))
print(dict(tot))
