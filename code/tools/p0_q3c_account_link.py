"""Q3c (phase 0b): account linking, cutoff-safe (files, activity and audit rows all <= audit_at).

Section A  original heuristic (workflow window + "owned by subject" exclusion) re-run cutoff-safe;
           window upper bound = min(audit_at, reported_at + 15 min).
Section B  subject-level linking: (1) timestamped identity/reference links from discover()
           (pre-deletion rows, customer/subject_reference, LINK_RESOURCE_IDENTITY, trace groups);
           (2) otherwise rank workflow candidates not owned by another user; measure defaults.
Section C  completion blockers on samples under the chosen default.
Section D  repeated requests per subject in the evaluation set.
"""
import re
from collections import Counter, defaultdict
from datetime import timedelta

from p0_q3_discovery import RECS, UID_RE, act, discover, eligible_files, email_owners, tokens
from p0_common import gold, read_csv, ts

ACC_RE = re.compile(r"\baccount_\d+\b")
req = {r["case_id"]: r for r in read_csv("sample_deletion_requests.csv")}


def owners_at(cut):
    """account -> users linked to it by any record/LINK activity available at or before cut."""
    e2u = email_owners(cut)
    own = defaultdict(set)
    for f in eligible_files(cut):
        for rec in RECS[f]:
            accs = set(ACC_RE.findall(rec))
            if not accs:
                continue
            us = {t if t.startswith("user_") else e2u.get(t) for t in tokens(rec)} - {None}
            us = {u for u in us if UID_RE.fullmatch(u)}
            for x in accs:
                own[x] |= us
    for a in act:
        if a["event_type"] == "LINK_RESOURCE_IDENTITY" and ts(a["event_time"]) <= cut:
            own[a["resource_id"]] |= set(UID_RE.findall(a["details"]))
    return own


def window(r):
    cut = ts(r["audit_at"])
    lo, hi = ts(r["requested_at"]), min(cut, ts(r["reported_at"]) + timedelta(minutes=15))
    return [a for a in act if a["event_type"] == "DELETE_RECORD" and a["target_system"] == "account_service"
            and lo <= ts(a["event_time"]) <= hi]


A, B, C = Counter(), Counter(), Counter()
dflt = Counter()
rows = []
for cid, (st, steps) in sorted(gold().items()):
    r = req[cid]
    cut, rep = ts(r["audit_at"]), ts(r["reported_at"])
    ga = [s["resource_id"] for s in steps if s["system_id"] == "account_service"][0]
    uid, vals, src = discover(r)
    own = owners_at(cut)
    win = window(r)
    cand = sorted({a["resource_id"] for a in win})
    # --- A: original heuristic, cutoff-safe
    mine = [x for x in cand if uid in own[x]]
    free = [x for x in cand if not own[x]]
    pick = mine[0] if len(mine) == 1 else (free[0] if len(free) == 1 and not mine else None)
    A["own_ok" if mine == [ga] else "free_unique_ok" if pick == ga else "ambiguous" if pick is None else "wrong"] += 1
    # --- B: subject-level priority linking
    linked = sorted(x for x, v in src.items() if x.startswith("account_") and v - {"EXP"})
    if len(linked) == 1:
        how, choice = "ref_link", linked[0]
    elif len(linked) > 1:
        how = "ref_link_multi"
        times = {a["resource_id"]: abs((ts(a["event_time"]) - rep).total_seconds()) for a in win}
        choice = min(linked, key=lambda x: (times.get(x, 1e12), x))
    else:
        ranked = [a for a in win if not (own[a["resource_id"]] - {uid})]  # not owned by another subject
        by = {
            "nearest_reported": sorted(ranked, key=lambda a: (abs((ts(a["event_time"]) - rep).total_seconds()), a["resource_id"])),
            "earliest_after_request": sorted(ranked, key=lambda a: (a["event_time"], a["resource_id"])),
            "latest_before_reported": sorted([a for a in ranked if ts(a["event_time"]) <= rep],
                                             key=lambda a: a["event_time"], reverse=True),
            "unique_only": ranked if len({a["resource_id"] for a in ranked}) == 1 else [],
        }
        for k, v in by.items():
            dflt[(k, "ok" if v and v[0]["resource_id"] == ga else "wrong" if v else "none")] += 1
        how = "workflow_rank"
        choice = by["nearest_reported"][0]["resource_id"] if by["nearest_reported"] else None
    B[(how, "ok" if choice == ga else "none" if choice is None else "wrong")] += 1
    rows.append((cid, st, ga, how, choice, len(cand)))
    # --- C: blockers under the chosen default (nearest_reported, flagged)
    if choice is None:
        C[f"unresolved_account:{st}"] += 1
    elif how == "workflow_rank":
        C[f"flagged_default:{st}:{'ok' if choice == ga else 'wrong'}"] += 1

print("A cutoff-safe original heuristic:", dict(A))
print("B subject-level linking:", dict(sorted(B.items())))
print("B defaults on ambiguous cases:", dict(sorted(dflt.items())))
print("C blockers:", dict(sorted(C.items())))
for x in rows:
    print("  ", *x)
# --- D: repeated requests per subject in the evaluation set (cutoff = each request's own audit_at)
allreq = read_csv("deletion_requests.csv")
latest = max(ts(r["audit_at"]) for r in allreq)
e2u = email_owners(latest)
per_user = defaultdict(list)
for r in allreq:
    per_user[e2u.get(r["email"].strip().lower(), "?" + r["email"])].append(r["case_id"])
rep_users = {u: c for u, c in per_user.items() if len(c) > 1}
print("D users with >1 request:", len(rep_users), "requests involved:", sum(len(c) for c in rep_users.values()),
      "unmapped emails:", sum(1 for u in per_user if u.startswith("?")))
print("  e.g.", sorted(rep_users.values())[:5])

# --- E: claim-aware ranking (ranking signal only, no one-to-one constraint). A workflow activity is
# "closest-claimed" by the request (any request file, grouped per subject) whose window contains it with
# the smallest |event_time - reported_at|. Prefer candidates this request closest-claims; then nearest.
every = read_csv("deletion_requests.csv") + read_csv("sample_deletion_requests.csv")
E = Counter()
for cid, (st, steps) in sorted(gold().items()):
    r = req[cid]
    cut, rep = ts(r["audit_at"]), ts(r["reported_at"])
    ga = [s["resource_id"] for s in steps if s["system_id"] == "account_service"][0]
    uid, vals, src = discover(r)
    if [x for x, v in src.items() if x.startswith("account_") and v - {"EXP"}]:
        continue  # resolved by reference links
    own = owners_at(cut)
    ranked = [a for a in window(r) if not (own[a["resource_id"]] - {uid})]

    def claimed_by_me(a):
        t = ts(a["event_time"])
        best = min((abs((t - ts(o["reported_at"])).total_seconds()), o["case_id"]) for o in every
                   if ts(o["requested_at"]) <= t <= ts(o["reported_at"]) + timedelta(minutes=15) and ts(o["requested_at"]) <= cut)
        return best[1] == cid
    order = sorted(ranked, key=lambda a: (not claimed_by_me(a), abs((ts(a["event_time"]) - rep).total_seconds()), a["resource_id"]))
    E["ok" if order and order[0]["resource_id"] == ga else "none" if not order else "wrong"] += 1
print("E claim-aware ranking on ambiguous cases:", dict(E))
