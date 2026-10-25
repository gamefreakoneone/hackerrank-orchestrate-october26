"""Q1: where does a record's data_category come from?  Q5: do condition-failure branches occur?"""
import re
from collections import Counter, defaultdict

from p0_common import gold, load_text, read_csv

text = load_text()
man = {m["file_id"]: m for m in read_csv("evidence_files.csv")}
cats = {r["data_category"] for r in read_csv("deletion_rules.csv")}
rt = Counter()
where = defaultdict(set)
for f, t in text.items():
    for m in re.finditer(r"record_type[\"']?\s*[:=]\s*[\"']?([A-Z_]+)", t):
        rt[m.group(1)] += 1
        where[m.group(1)].add(f)
    for c in cats:
        if c in t:
            where["CAT:" + c].add(f)
print("record_type values:", dict(rt))
print({k: len(v) for k, v in sorted(where.items())})
# tables / collections
tbl = Counter(re.findall(r"CREATE TABLE \"?(\w+)", "\n".join(text.values())))
col = Counter(re.findall(r"\"collection(?:_name)?\"\s*:\s*\"(\w+)\"", "\n".join(text.values())))
print("tables:", sorted(tbl)); print("collections:", sorted(col))
# gold: (prefix, action family) combos and how the cited record states its category
fam = Counter()
for cid, (st, steps) in gold().items():
    for s in steps:
        op = s["operation"]
        if op in ("DELETE_RECORD", "REDACT_RECORD", "ANONYMIZE_RECORD", "VERIFY_RECORD_ABSENT", "VERIFY_RECORD_REDACTED", "VERIFY_RECORD_ANONYMIZED", "VERIFY_RECORD_PRESENT"):
            fam[(s["resource_id"].rsplit("_", 1)[0], op.split("_")[-1])] += 1
print("gold prefix x end-state:", sorted(fam.items()))
# Q5 signals
for kw in ["shared", "other customer", "another customer", "hold_status", "legal_hold", "released", "expired", "retention_until", "hold_until", "attachment_owner", "belongs"]:
    hits = sorted(f for f, t in text.items() if kw.lower() in t.lower())
    print(f"kw {kw!r}: {len(hits)} files", hits[:6])
