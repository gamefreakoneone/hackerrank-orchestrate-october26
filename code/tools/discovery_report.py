"""Discovery and account-linkage report on the samples (reads gold: evaluation only, never the pipeline).

python code/tools/discovery_report.py [--split dev|holdout|all] [--verbose]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODE_DIR))
sys.path.insert(0, str(CODE_DIR / "evaluation"))

import score  # noqa: E402
from ghostaudit.account_link import link_account  # noqa: E402
from ghostaudit.discovery import discover  # noqa: E402
from ghostaudit.evidence.index import build_ledger  # noqa: E402
from ghostaudit.evidence.vision import vision_observations  # noqa: E402
from ghostaudit.identity import identifier_owner_index, resolve  # noqa: E402
from ghostaudit.loaders import load_dataset  # noqa: E402


def main(argv: list[str] | None = None) -> dict:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=["dev", "holdout", "all"], default="all")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)
    dataset = load_dataset(CODE_DIR.parent / "dataset", sample=True)
    ledger = build_ledger(dataset, extra=vision_observations(dataset, offline=True))
    gold = score.read_rows(CODE_DIR.parent / "dataset" / "sample_output.csv")
    case_ids = set(score.split_case_ids(args.split, gold))
    totals, linkage, provenance = Counter(), Counter(), Counter()
    for request in dataset.requests:
        if request.case_id not in case_ids:
            continue
        subject = resolve(request, dataset)
        discovered = discover(subject, request, dataset, ledger)
        owners = identifier_owner_index(dataset, request.audit_at)
        link = link_account(subject, request, discovered, dataset, ledger, owners)
        gold_steps = gold[request.case_id][1]
        gold_resources = {s["resource_id"] for s in gold_steps}
        gold_accounts = {s["resource_id"] for s in gold_steps if s["system_id"] == "account_service"}
        grounded = {rid for rid, d in discovered.items() if d.grounded}
        found_non_account = {r for r in grounded if not r.startswith("account_")}
        planned_accounts = ({link.current, *link.historical} - {None}) if link.via != "ungrounded" else set()
        hits = (found_non_account | planned_accounts) & gold_resources
        extras = (found_non_account | planned_accounts) - gold_resources
        totals.update(gold=len(gold_resources), found=len(hits), extra=len(extras))
        for rid in hits:
            provenance["+".join(sorted(discovered[rid].vias))] += 1
        outcome = ("ungrounded" if link.via == "ungrounded" else
                   "correct" if link.current in gold_accounts else "wrong")
        linkage[(link.via, outcome)] += 1
        if args.verbose or outcome == "wrong":
            print(request.case_id, gold[request.case_id][0], "account:", link.via, link.current, link.historical,
                  "gold", sorted(gold_accounts), "| missed", sorted(gold_resources - hits), "| extra", sorted(extras),
                  "| ranked", link.ranked_candidates[:3])
    cases = sum(linkage.values())
    correct = sum(v for (via, o), v in linkage.items() if o == "correct")
    wrong = sum(v for (via, o), v in linkage.items() if o == "wrong")
    result = {
        "cases": cases, "resource_recall": f"{totals['found']}/{totals['gold']}", "extra_resources": totals["extra"],
        "linkage": {f"{via}:{o}": v for (via, o), v in sorted(linkage.items())},
        "linkage_accuracy": f"{correct}/{cases}", "linkage_precision": f"{correct}/{correct + wrong}",
        "provenance_of_hits": dict(provenance.most_common()),
    }
    print(json.dumps(result, indent=1))
    return result


if __name__ == "__main__":
    main()
