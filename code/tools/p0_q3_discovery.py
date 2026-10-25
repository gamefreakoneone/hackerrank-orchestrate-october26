"""Q3: discovery recall with exact identifier matching and per-case cutoffs (phase 0b).

Cutoff-safe: evidence files need captured_at <= audit_at, activity rows event_time <= audit_at,
audit-log rows event_time <= audit_at; the subject's identity is the current snapshot with later
changes reverted. Exact matching: emails / user_ids / sha256 hashes are compared as whole tokens,
names and phones must not be embedded in a longer word or number (no `Jonas Berg` in `Jonas Berglund`).

Sources:
  ID  : resource ids co-occurring with a subject identifier in one evidence record
        (SQL row / JSON object / log trace_id group / PDF / txt line)
  LNK : LINK_RESOURCE_IDENTITY activity naming a subject email or user_id
  EXP : one hop: resources co-occurring with an already-found resource (reported separately)
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict

from p0_common import RES_RE, gold, load_text, read_csv, ts

text = load_text()
man = {m["file_id"]: m for m in read_csv("evidence_files.csv")}
ids = {u["user_id"]: u for u in read_csv("user_identities.csv")}
audit = read_csv("user_audit_log.csv")
act = read_csv("system_activity.csv")
FIELD = {"email": "email", "phone": "phone", "email_hash": "email_hash"}
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
UID_RE = re.compile(r"\buser_\d+\b")
HASH_RE = re.compile(r"\b[0-9a-f]{64}\b")
TRACE_RE = re.compile(r'trace_id["=:\s]+"?([\w-]+)')


def records(fid):
    t = text[fid]
    p = man[fid]["file_path"]
    if p.endswith(".json"):
        out = []

        def walk(o):
            if isinstance(o, dict):
                if any(isinstance(v, str) and RES_RE.fullmatch(v) for v in o.values()):
                    out.append(json.dumps(o, ensure_ascii=False))
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


RECS = {f: records(f) for f in text}


MODE = "strict"  # "strict": post-cutoff audit rows are never read; "revert": undo post-cutoff changes (0b)


def identity_at(uid, cut, mode=None):
    """Identifier values of `uid` usable at `cut`.

    strict: old/new values of audit rows with event_time <= cut (post-cutoff rows unread), plus the current snapshot
            only if its updated_at <= cut (otherwise its values are unavailable and excluded).
    revert: current snapshot with post-cutoff changes reverted (reads post-cutoff rows; phase 0b behaviour).
    """
    mode = mode or MODE
    u = ids[uid]
    snapshot_ok = mode == "revert" or ts(u["updated_at"]) <= cut  # strict: a post-cutoff snapshot is unavailable
    cur = {"email": u["email"], "phone": u["phone"], "email_hash": u["email_hash"]} if snapshot_ok else {}
    vals = {uid, u["name"]} if snapshot_ok else {uid}
    for a in sorted(audit, key=lambda a: a["event_time"], reverse=True):
        if a["user_id"] != uid:
            continue
        if ts(a["event_time"]) > cut:
            if mode == "revert":
                cur[FIELD[a["field_name"]]] = a["old_value"]  # revert a change made after the cutoff
        else:
            vals |= {a["old_value"], a["new_value"]}
    vals |= set(cur.values())
    vals |= {hashlib.sha256(v.encode()).hexdigest() for v in list(vals) if "@" in v}
    return {v for v in vals if v}


def email_owners(cut):
    """email -> user_id using only identity values valid at or before `cut`."""
    out = {}
    for uid in ids:
        for v in identity_at(uid, cut):
            if "@" in v:
                out[v.lower()] = uid
    return out


def subject(email, cut):
    owners = email_owners(cut)
    uid = owners.get(email.strip().lower())
    return uid, (identity_at(uid, cut) if uid else {email})


def tokens(rec):
    return ({e.lower() for e in EMAIL_RE.findall(rec)} | set(UID_RE.findall(rec))
            | set(HASH_RE.findall(rec)))


def hit(rec, vals):
    """Exact identifier match: whole-token emails/user_ids/hashes; bounded names and phones."""
    if tokens(rec) & {v.lower() for v in vals}:
        return True
    for v in vals:
        if "@" in v or v.startswith("user_") or HASH_RE.fullmatch(v):
            continue
        bound = r"(?<![\d+])" + re.escape(v) + r"(?!\d)" if v.startswith("+") else \
            r"(?<!\w)" + re.escape(v) + r"(?!\w)"
        if re.search(bound, rec):
            return True
    return False


def eligible_files(cut):
    return [f for f in text if ts(man[f]["captured_at"]) <= cut]


def discover(r):
    cut = ts(r["audit_at"])
    uid, vals = subject(r["email"], cut)
    src = defaultdict(set)
    elig = eligible_files(cut)
    for f in elig:
        for rec in RECS[f]:
            if hit(rec, vals):
                for x in RES_RE.findall(rec):
                    src[x].add("ID")
    for a in act:
        if ts(a["event_time"]) <= cut and a["event_type"] == "LINK_RESOURCE_IDENTITY" and hit(a["details"], vals):
            src[a["resource_id"]].add("LNK")
    found = set(src)
    for f in elig:
        for rec in RECS[f]:
            xs = set(RES_RE.findall(rec))
            if xs & found:
                for x in xs - found:
                    src[x].add("EXP")
    return uid, vals, src


if __name__ == "__main__":
    req = {r["case_id"]: r for r in read_csv("sample_deletion_requests.csv")}
    tot = defaultdict(int)
    for cid, (status, steps) in sorted(gold().items()):
        uid, vals, src = discover(req[cid])
        g = {s["resource_id"] for s in steps}
        direct = {x for x, v in src.items() if v - {"EXP"}}
        tot["gold"] += len(g)
        tot["found_direct"] += len(g & direct)
        tot["found_with_EXP"] += len(g & set(src))
        tot["extra_direct"] += len(direct - g)
        tot["extra_EXP_only"] += len(set(src) - direct - g)
        print(cid, status, "miss=", sorted(g - direct), "extra=", sorted(direct - g)[:6], len(direct - g))
    print(dict(tot))
