"""Grader-replica scorer for the 32 samples (an inspected regression set, not a holdout).

python code/evaluation/score.py PRED GOLD [--split dev|holdout|all] [--diagnostics PATH]
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

EVALUATION_DIR = Path(__file__).resolve().parent
SPLIT_PATH = EVALUATION_DIR / "split.json"
DIAGNOSTIC_FLAGS = ["ACCOUNT_UNGROUNDED", "ACCOUNT_MULTI_GROUNDED", "UNKNOWN_STATE", "POLICY_UNDEFINED",
                    "EMPTY_OBLIGATIONS", "REQUIRED_RECORD_MISSING", "CONDITION_DEFAULTED", "ACTIVITY_CITATION",
                    "IDENTITY_SNAPSHOT_AFTER_CUTOFF"]
MATCHED_FIELDS = ["phase", "state", "evidence_id", "step_no"]


def read_rows(path: Path) -> dict[str, tuple[str, list[dict]]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return {r["case_id"]: (r["deletion_status"], json.loads(r["steps_json"])) for r in csv.DictReader(handle)}


def read_diagnostics(path: Path | None) -> dict[str, dict]:
    if path is None or not path.is_file():
        return {}
    return {d["case_id"]: d for d in map(json.loads, path.read_text(encoding="utf-8").splitlines()) if d}


def split_case_ids(split: str, gold: dict) -> list[str]:
    if split == "all":
        return sorted(gold, key=lambda c: int(c.split("_")[1]))
    return json.loads(SPLIT_PATH.read_text())[split]


def step_key(step: dict) -> tuple[str, str, str]:
    return step["operation"], step["system_id"], step["resource_id"]


def lcs_length(a: list, b: list) -> int:
    previous = [0] * (len(b) + 1)
    for item_a in a:
        current = [0]
        for j, item_b in enumerate(b, start=1):
            current.append(previous[j - 1] + 1 if item_a == item_b else max(previous[j], current[j - 1]))
        previous = current
    return previous[-1]


def account_linkage(gold_steps: list[dict], diagnostics: dict | None) -> str:
    """correct | wrong | ungrounded | no_gold_account | not_measured (no diagnostics)."""
    gold_accounts = {s["resource_id"] for s in gold_steps if s["system_id"] == "account_service"}
    if not gold_accounts:
        return "no_gold_account"
    if diagnostics is None or "account_link" not in diagnostics:
        return "not_measured"
    link = diagnostics["account_link"]
    if link.get("via") == "ungrounded" or not link.get("current"):
        return "ungrounded"
    return "correct" if link["current"] in gold_accounts else "wrong"


def score(pred: dict, gold: dict, case_ids: list[str], diagnostics: dict[str, dict]) -> dict:
    totals = Counter()
    field_hits = Counter()
    linkage = Counter()
    flag_counts = Counter()
    lcs_sum = 0.0
    per_case = []
    for case_id in case_ids:
        gold_status, gold_steps = gold[case_id]
        pred_status, pred_steps = pred.get(case_id, ("MISSING", []))
        gold_by_key = {step_key(s): s for s in gold_steps}
        pred_by_key = {step_key(s): s for s in pred_steps}
        matched = sorted(set(gold_by_key) & set(pred_by_key))
        for key in matched:
            for field_name in MATCHED_FIELDS:
                field_hits[field_name] += gold_by_key[key][field_name] == pred_by_key[key][field_name]
        status_ok = pred_status == gold_status
        sequence_ok = pred_steps == gold_steps
        gold_keys, pred_keys = [step_key(s) for s in gold_steps], [step_key(s) for s in pred_steps]
        longest = max(len(gold_keys), len(pred_keys))
        lcs_ratio = lcs_length(gold_keys, pred_keys) / longest if longest else 1.0
        case_diagnostics = diagnostics.get(case_id)
        link_result = account_linkage(gold_steps, case_diagnostics)
        linkage[link_result] += 1
        for flag in (case_diagnostics or {}).get("flags", []):
            flag_counts[flag] += 1
        totals.update(cases=1, status_ok=status_ok, sequence_ok=sequence_ok, matched=len(matched),
                      gold_steps=len(gold_steps), pred_steps=len(pred_steps))
        lcs_sum += lcs_ratio
        per_case.append({"case_id": case_id, "gold": gold_status, "pred": pred_status, "status_ok": status_ok,
                         "gold_steps": len(gold_steps), "pred_steps": len(pred_steps), "matched": len(matched),
                         "sequence_ok": sequence_ok, "lcs": round(lcs_ratio, 3), "account": link_result,
                         "flags": sorted((case_diagnostics or {}).get("flags", []))})
    precision = totals["matched"] / totals["pred_steps"] if totals["pred_steps"] else 0.0
    recall = totals["matched"] / totals["gold_steps"] if totals["gold_steps"] else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    cases = totals["cases"] or 1
    with_gold_account = sum(v for k, v in linkage.items() if k != "no_gold_account")
    return {
        "cases": totals["cases"],
        "status_accuracy": totals["status_ok"] / cases,
        "step_precision": precision, "step_recall": recall, "step_f1": f1,
        "field_accuracy": {f: (field_hits[f] / totals["matched"] if totals["matched"] else 0.0)
                           for f in MATCHED_FIELDS},
        "sequence_exact": totals["sequence_ok"] / cases,
        "mean_lcs": lcs_sum / cases,
        "account_linkage": dict(sorted(linkage.items())),
        "account_linkage_accuracy": linkage["correct"] / with_gold_account if with_gold_account else 0.0,
        "account_linkage_precision": (linkage["correct"] / (linkage["correct"] + linkage["wrong"])
                                      if linkage["correct"] + linkage["wrong"] else 0.0),
        "flag_counts": {flag: flag_counts[flag] for flag in DIAGNOSTIC_FLAGS},
        "totals": dict(totals),
        "per_case": per_case,
    }


def render_markdown(result: dict, title: str) -> str:
    t = result["totals"]
    lines = [
        f"# {title}",
        "",
        "Samples are an inspected regression set (Phase 0), not untouched validation.",
        "",
        "| Metric | Value |", "|---|---|",
        f"| Cases | {result['cases']} |",
        f"| Status accuracy | {result['status_accuracy']:.3f} ({t.get('status_ok', 0)}/{result['cases']}) |",
        f"| Account linkage accuracy | {result['account_linkage_accuracy']:.3f} {result['account_linkage']} |",
        f"| Account linkage precision (grounded) | {result['account_linkage_precision']:.3f} |",
        f"| Step precision / recall / F1 | {result['step_precision']:.3f} / {result['step_recall']:.3f} / "
        f"{result['step_f1']:.3f} ({t.get('matched', 0)} matched, {t.get('pred_steps', 0)} pred, "
        f"{t.get('gold_steps', 0)} gold) |",
        *[f"| Field accuracy on matched: {k} | {v:.3f} |" for k, v in result["field_accuracy"].items()],
        f"| Sequence exact match | {result['sequence_exact']:.3f} ({t.get('sequence_ok', 0)}/{result['cases']}) |",
        f"| Mean normalized LCS | {result['mean_lcs']:.3f} |",
        "",
        "| Flag | Cases |", "|---|---|",
        *[f"| {k} | {v} |" for k, v in result["flag_counts"].items()],
        "",
        "| case | gold | pred | ok | gold steps | pred steps | matched | seq | LCS | account | flags |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
        *[f"| {c['case_id']} | {c['gold']} | {c['pred']} | {'Y' if c['status_ok'] else 'N'} | {c['gold_steps']} | "
          f"{c['pred_steps']} | {c['matched']} | {'Y' if c['sequence_ok'] else 'N'} | {c['lcs']} | {c['account']} | "
          f"{' '.join(c['flags'])} |" for c in result["per_case"]],
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> dict:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pred", type=Path)
    parser.add_argument("gold", type=Path)
    parser.add_argument("--split", choices=["dev", "holdout", "all"], default="all")
    parser.add_argument("--diagnostics", type=Path, default=None,
                        help="diagnostics JSONL (default: <pred stem>.diagnostics.jsonl next to PRED if present)")
    args = parser.parse_args(argv)
    diagnostics_path = args.diagnostics or args.pred.with_suffix(".diagnostics.jsonl")
    gold = read_rows(args.gold)
    result = score(read_rows(args.pred), gold, split_case_ids(args.split, gold), read_diagnostics(diagnostics_path))
    print(render_markdown(result, f"Score: {args.pred.name} vs {args.gold.name} (split={args.split})"))
    return result


if __name__ == "__main__":
    main(sys.argv[1:])
