"""Dataset reconnaissance for Ghost Data Still Exists (spec 0002).

Run from anywhere:  python code/recon.py
Writes:             code/docs/DATA_NOTES.md

Standard library only. Optional: `pip install pypdf` to check PDF text layers.
Read-only: never modifies anything under dataset/.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

# ---------- paths ----------
HERE = Path(__file__).resolve().parent
ROOT = next((p for p in [HERE, *HERE.parents] if (p / "dataset").is_dir()), None)
if ROOT is None:
    sys.exit("Could not find a dataset/ folder above this script.")
DS = ROOT / "dataset"
OUT = ROOT / "code" / "docs" / "DATA_NOTES.md"

lines: list[str] = []


def h(title: str) -> None:
    lines.append(f"\n## {title}\n")


def p(text: str = "") -> None:
    lines.append(text)


def table(rows: list[tuple], headers: tuple) -> None:
    p("| " + " | ".join(headers) + " |")
    p("|" + "---|" * len(headers))
    for r in rows:
        p("| " + " | ".join(str(c).replace("|", "\\|").replace("\n", " ") for c in r) + " |")
    p()


def read_csv(name: str) -> list[dict]:
    path = DS / name
    if not path.exists():
        p(f"**MISSING:** `{name}`")
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def short(s: str, n: int = 160) -> str:
    s = (s or "").replace("\n", " ")
    return s if len(s) <= n else s[: n - 1] + "…"


# ---------- 1. CSV inventory ----------
h("1. CSV inventory")
inv = []
data: dict[str, list[dict]] = {}
for path in sorted(DS.glob("*.csv")):
    rows = read_csv(path.name)
    data[path.name] = rows
    cols = list(rows[0].keys()) if rows else []
    inv.append((path.name, len(rows), ", ".join(cols)))
table(inv, ("file", "rows", "columns"))

requests = data.get("deletion_requests.csv", [])
samples = data.get("sample_deletion_requests.csv", [])
gold = data.get("sample_output.csv", [])
identities = data.get("user_identities.csv", [])
audit = data.get("user_audit_log.csv", [])
activity = data.get("system_activity.csv", [])
rules = data.get("deletion_rules.csv", [])
manifest = data.get("evidence_files.csv", [])

# ---------- 2. case_id format ----------
h("2. case_id format (sorting safety)")
for name, rows in (("deletion_requests", requests), ("sample", samples)):
    lens = Counter(len(r["case_id"]) for r in rows)
    p(f"- {name}: id lengths {dict(lens)}; first={rows[0]['case_id'] if rows else '-'}, last={rows[-1]['case_id'] if rows else '-'}")
p("- If lengths vary, sort numerically on the suffix, not lexically.")

# ---------- 3. request fields ----------
h("3. Request fields")
for col in ("reported_status",):
    p(f"- `{col}` in requests: {dict(Counter(r[col] for r in requests))}")
non_ascii = sum(1 for r in requests if any(ord(c) > 127 for c in r["request_text"]))
p(f"- request_text with non-ASCII chars (likely non-English): {non_ascii}/{len(requests)}")
p("\n**Samples: request text vs gold status** (learn the intent boundary):\n")
gold_by = {g["case_id"]: g for g in gold}
table(
    [(s["case_id"], gold_by.get(s["case_id"], {}).get("deletion_status", "?"), s["reported_status"], short(s["request_text"], 140)) for s in samples],
    ("case", "gold", "reported", "request_text"),
)

# ---------- 4. identity hash scheme ----------
h("4. email_hash scheme")
schemes = {
    "sha256(raw)": lambda e: hashlib.sha256(e.encode()).hexdigest(),
    "sha256(lower.strip)": lambda e: hashlib.sha256(e.strip().lower().encode()).hexdigest(),
    "md5(lower.strip)": lambda e: hashlib.md5(e.strip().lower().encode()).hexdigest(),
    "sha1(lower.strip)": lambda e: hashlib.sha1(e.strip().lower().encode()).hexdigest(),
}
for name, fn in schemes.items():
    hits = sum(1 for r in identities if r.get("email_hash", "").lower() == fn(r.get("email", "")))
    p(f"- {name}: {hits}/{len(identities)} match")

h("5. Audit log fields")
p(f"- field_name counts: {dict(Counter(r['field_name'] for r in audit))}")
req_emails = {r["email"].strip().lower() for r in requests}
cur_emails = {r["email"].strip().lower() for r in identities}
hist_emails = {r[k].strip().lower() for r in audit if "email" in r["field_name"].lower() for k in ("old_value", "new_value") if r[k]}
p(f"- request emails matching a CURRENT identity: {len(req_emails & cur_emails)}/{len(req_emails)}")
p(f"- request emails matching only HISTORY: {len((req_emails & hist_emails) - cur_emails)}")
p(f"- request emails matching nothing: {len(req_emails - cur_emails - hist_emails)}")

# ---------- 6. activity ----------
h("6. system_activity")
p(f"- event_type × reported_result:")
ct = Counter((r["event_type"], r["reported_result"]) for r in activity)
table(sorted((e, res, n) for (e, res), n in ct.items()), ("event_type", "result", "count"))
p(f"- source_system values: {sorted({r['source_system'] for r in activity})}")
p(f"- target_system values: {sorted({r['target_system'] for r in activity})}")
prefixes = Counter(re.sub(r"[_-]?\d+$", "", r["resource_id"]) for r in activity if r["resource_id"])
p(f"- resource_id prefixes: {dict(prefixes)}")
p("\n**`details` examples per event_type (3 each):**\n")
by_type = defaultdict(list)
for r in activity:
    if len(by_type[r["event_type"]]) < 3:
        by_type[r["event_type"]].append(r)
for et in sorted(by_type):
    p(f"- **{et}**")
    for r in by_type[et]:
        p(f"  - `{r['activity_id']}` {r['source_system']}→{r['target_system']} {r['resource_id']} [{r['reported_result']}]: {short(r['details'], 220)}")

# ---------- 7. rules ----------
h("7. deletion_rules")
table([(r["rule_id"], r["data_category"], r["condition"], r["required_action"]) for r in rules], ("rule", "category", "condition", "action"))
categories = [r["data_category"] for r in rules]

# ---------- 8. evidence ----------
h("8. Evidence manifest and files")
p(f"- origin values: {dict(Counter(r['origin'] for r in manifest))}")


def resolve(fp: str) -> Path | None:
    for base in (DS, DS / "evidence", ROOT):
        cand = base / fp
        if cand.exists():
            return cand
    return None


exts = Counter()
missing = []
files: dict[str, Path] = {}
for r in manifest:
    path = resolve(r["file_path"])
    if path is None:
        missing.append(r["file_id"])
        continue
    files[r["file_id"]] = path
    exts[path.suffix.lower()] += 1
p(f"- extensions: {dict(exts)}; unresolved paths: {missing[:10]}{' …' if len(missing) > 10 else ''}")

origin_by_id = {r["file_id"]: r["origin"] for r in manifest}
captured_by_id = {r["file_id"]: r["captured_at"] for r in manifest}

# 8a SQL
p("\n### 8a. SQL snapshots\n")
cat_pat = re.compile("|".join(map(re.escape, categories))) if categories else None
for fid, path in files.items():
    if path.suffix.lower() != ".sql":
        continue
    con = sqlite3.connect(":memory:")
    try:
        con.executescript(path.read_text(encoding="utf-8", errors="replace"))
    except sqlite3.Error as e:
        p(f"- `{fid}` {path.name}: **load error** {e}")
        continue
    p(f"- `{fid}` {path.name} (origin={origin_by_id.get(fid)}, captured={captured_by_id.get(fid)})")
    for (tname,) in con.execute("SELECT name FROM sqlite_master WHERE type='table'"):
        cols = [c[1] for c in con.execute(f'PRAGMA table_info("{tname}")')]
        n = con.execute(f'SELECT COUNT(*) FROM "{tname}"').fetchone()[0]
        p(f"  - table `{tname}` ({n} rows): {cols}")
        for c in cols:
            if re.search(r"category|status|state|type|hold|retention|restore|enabled|active", c, re.I):
                vals = [v[0] for v in con.execute(f'SELECT DISTINCT "{c}" FROM "{tname}" LIMIT 8')]
                p(f"    - `{c}` values: {vals}")
    con.close()

# 8b JSON
p("\n### 8b. JSON files (key paths)\n")


def key_paths(obj, prefix="", out=None, depth=0):
    out = out if out is not None else Counter()
    if depth > 4:
        return out
    if isinstance(obj, dict):
        for k, v in obj.items():
            out[prefix + k] += 1
            key_paths(v, prefix + k + ".", out, depth + 1)
    elif isinstance(obj, list):
        for v in obj[:20]:
            key_paths(v, prefix + "[]." if prefix else "[].", out, depth + 1)
    return out


for fid, path in files.items():
    if path.suffix.lower() != ".json":
        continue
    try:
        obj = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        keys = list(key_paths(obj).keys())[:25]
        p(f"- `{fid}` {path.name} (origin={origin_by_id.get(fid)}): {keys}")
    except json.JSONDecodeError as e:
        p(f"- `{fid}` {path.name}: invalid JSON ({e})")

# 8c text/logs
p("\n### 8c. Logs / text (first 2 lines)\n")
for fid, path in files.items():
    if path.suffix.lower() in (".log", ".txt", ".csv", ".jsonl", ".md"):
        head = path.read_text(encoding="utf-8", errors="replace").splitlines()[:2]
        p(f"- `{fid}` {path.name} (origin={origin_by_id.get(fid)}): " + " ⏎ ".join(short(x, 150) for x in head))

# 8d PDF/images
p("\n### 8d. PDFs and images\n")
try:
    from pypdf import PdfReader  # type: ignore
except ImportError:
    PdfReader = None
    p("- pypdf not installed; skipping text-layer check (`pip install pypdf`).")
for fid, path in files.items():
    ext = path.suffix.lower()
    if ext == ".pdf" and PdfReader:
        try:
            txt = "".join((pg.extract_text() or "") for pg in PdfReader(str(path)).pages)
            p(f"- `{fid}` {path.name}: text layer {len(txt)} chars — {short(txt, 120)}")
        except Exception as e:  # noqa: BLE001
            p(f"- `{fid}` {path.name}: read error {e}")
    elif ext in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
        p(f"- `{fid}` {path.name} (origin={origin_by_id.get(fid)}): image, needs vision")

# 8e keyword sweep across all evidence + activity details
p("\n### 8e. Where do categories / retention / holds appear?\n")
sweep = {k: [] for k in ["category tokens", "retention", "legal hold", "restore", "tombstone"]}
pats = {
    "category tokens": cat_pat,
    "retention": re.compile(r"retention|retain", re.I),
    "legal hold": re.compile(r"legal[_ ]?hold", re.I),
    "restore": re.compile(r"restor", re.I),
    "tombstone": re.compile(r"tombstone", re.I),
}
for fid, path in files.items():
    if path.suffix.lower() in (".pdf", ".png", ".jpg", ".jpeg", ".webp", ".gif"):
        continue
    text = path.read_text(encoding="utf-8", errors="replace")
    for k, pat in pats.items():
        if pat and pat.search(text):
            sweep[k].append(fid)
for r in activity:
    for k, pat in pats.items():
        if pat and pat.search(r["details"] or ""):
            sweep[k].append(r["activity_id"])
for k, ids in sweep.items():
    p(f"- {k}: {len(ids)} hits, e.g. {ids[:8]}")

# ---------- 9. gold output analysis ----------
h("9. sample_output: what the gold answers look like")
act_by_id = {r["activity_id"]: r for r in activity}
audit_ids = {r["audit_id"] for r in audit}
p(f"- status counts: {dict(Counter(g['deletion_status'] for g in gold))}")
op_ct = Counter()
cite_kind = defaultdict(Counter)
sys_res = defaultdict(set)
flow_rows = []
for g in gold:
    steps = json.loads(g["steps_json"])
    for s in steps:
        op = s["operation"]
        op_ct[(g["deletion_status"], s["phase"], op)] += 1
        sys_res[op].add(f"{s['system_id']}/{re.sub(r'[_-]?\d+$', '', s['resource_id'])}")
        ev = s["evidence_id"]
        if not ev:
            kind = "empty"
        elif ev in act_by_id:
            kind = f"activity:{act_by_id[ev]['event_type']}"
        elif ev in audit_ids:
            kind = "audit_id"
        elif ev in origin_by_id:
            kind = f"file:{files[ev].suffix if ev in files else '?'}:{origin_by_id[ev]}"
        else:
            kind = "UNKNOWN_ID"
        cite_kind[op][kind] += 1
        if "FLOW" in op or "RESTORE" in op:
            flow_rows.append((g["case_id"], g["deletion_status"], op, s["system_id"], s["resource_id"], ev, kind))
table(sorted((st, ph, op, n) for (st, ph, op), n in op_ct.items()), ("status", "phase", "operation", "count"))
p("**Evidence type cited per operation:**\n")
table([(op, dict(c)) for op, c in sorted(cite_kind.items())], ("operation", "cited evidence kinds"))
p("**system_id/resource-prefix pairs per operation:**\n")
table([(op, sorted(v)) for op, v in sorted(sys_res.items())], ("operation", "system/resource prefixes"))
p("**Flow and restore steps (Q3):**\n")
table(flow_rows, ("case", "status", "op", "system_id", "resource_id", "evidence", "kind"))

# ---------- 10. ordering check on gold ----------
h("10. Does gold follow the canonical sort?")
ORDER = ["REPORT_REMAINING_RECORD", "REPORT_EXPOSED_PII", "REPORT_ACTIVE_DATA_FLOW", "REPORT_RESTORE_RISK",
         "DISABLE_DATA_FLOW", "BLOCK_RESTORE", "DELETE_RECORD", "REDACT_RECORD", "ANONYMIZE_RECORD",
         "VERIFY_RECORD_ABSENT", "VERIFY_RECORD_PRESENT", "VERIFY_RECORD_REDACTED", "VERIFY_RECORD_ANONYMIZED",
         "VERIFY_DATA_FLOW_DISABLED", "VERIFY_RESTORE_BLOCKED"]
rank = {o: i for i, o in enumerate(ORDER)}
bad = []
for g in gold:
    steps = json.loads(g["steps_json"])
    keys = [(rank.get(s["operation"], 99), s["system_id"], s["resource_id"]) for s in steps]
    if keys != sorted(keys) or [s["step_no"] for s in steps] != list(range(1, len(steps) + 1)):
        bad.append(g["case_id"])
p(f"- cases violating (op_rank, system_id, resource_id) sort: {bad or 'none'}")
p("- If 'none', the canonical sort is the whole ordering story; no dependency logic needed.")

# ---------- write ----------
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("# Dataset reconnaissance (generated by code/recon.py)\n" + "\n".join(lines) + "\n", encoding="utf-8")
print(f"Wrote {OUT.relative_to(ROOT)}")