"""Discovery and account-linkage report on the samples (reads gold: evaluation only, never the pipeline).
Every missed gold resource is classified by the participant-visible evidence available for it (spec 0019).

python code/tools/discovery_report.py [--split dev|holdout|all] [--verbose] [--out result.json]
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
from ghostaudit.evidence.index import eligible  # noqa: E402
from ghostaudit.identity import identifier_owner_index, resolve  # noqa: E402
from ghostaudit.loaders import load_dataset  # noqa: E402


def miss_cause(resource_id, subject, request, dataset, ledger, owners) -> str:
    """Why a gold resource is not grounded, judged only from participant-visible evidence (first match wins)."""
    observations = ledger.by_resource.get(resource_id, [])
    usable = [o for o in observations if eligible(o, request.audit_at)]
    link_keys = subject.key_values() - subject.names
    if any(o.identifiers & link_keys for o in usable):
        return "discovery_gap"                         # a subject identifier is parsed but did not link
    if any(key in (value or "") for o in usable for value in o.fields.values() for key in link_keys):
        return "parser_gap_candidate"                  # a subject identifier is in the record text but not parsed
    if any(owners.get(identifier, set()) - {subject.user_id} for o in usable for identifier in o.identifiers):
        return "linked_to_other_user"
    if usable:
        return "eligible_records_without_ownership"    # e.g. null profile / 404, anonymized record
    if any(a.resource_id == resource_id and a.event_time <= request.audit_at for a in dataset.activity):
        return "workflow_claims_only"                  # operational claims: ranked candidates at most
    if observations:
        return "post_cutoff_evidence_only"
    return "no_participant_evidence"


def main(argv: list[str] | None = None) -> dict:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=["dev", "holdout", "all"], default="all")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--out", type=Path, help="also write the result (with the per-miss gap table) as JSON")
    args = parser.parse_args(argv)
    dataset = load_dataset(CODE_DIR.parent / "dataset", sample=True)
    ledger = build_ledger(dataset, extra=vision_observations(dataset, offline=True))
    gold = score.read_rows(CODE_DIR.parent / "dataset" / "sample_output.csv")
    case_ids = set(score.split_case_ids(args.split, gold))
    totals, linkage, provenance, causes = Counter(), Counter(), Counter(), Counter()
    gap_table = []
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
        totals.update(gold=len(gold_resources), found=len(hits), extra=len(extras),
                      gold_accounts=len(gold_accounts), found_accounts=len(hits & gold_accounts),
                      extra_accounts=len({r for r in extras if r.startswith("account_")}))
        for rid in sorted(gold_resources - hits):
            cause = miss_cause(rid, subject, request, dataset, ledger, owners)
            causes[cause] += 1
            gap_table.append({"case_id": request.case_id, "resource_id": rid, "cause": cause})
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
        "account_recall": f"{totals['found_accounts']}/{totals['gold_accounts']}",
        "other_resource_recall": f"{totals['found'] - totals['found_accounts']}/"
                                 f"{totals['gold'] - totals['gold_accounts']}",
        "extra_accounts": totals["extra_accounts"], "miss_causes": dict(causes.most_common()),
        "linkage": {f"{via}:{o}": v for (via, o), v in sorted(linkage.items())},
        "linkage_accuracy": f"{correct}/{cases}", "linkage_precision": f"{correct}/{correct + wrong}",
        "provenance_of_hits": dict(provenance.most_common()),
    }
    print(json.dumps(result, indent=1))
    if args.verbose:
        for row in gap_table:
            print(row["case_id"], row["resource_id"], row["cause"])
    if args.out:
        args.out.write_text(json.dumps({**result, "gap_table": gap_table}, indent=1, sort_keys=True) + "\n",
                            encoding="utf-8")
    return result


if __name__ == "__main__":
    main()
