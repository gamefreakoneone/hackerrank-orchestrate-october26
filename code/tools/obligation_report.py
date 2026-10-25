"""Obligations vs gold on the samples (evaluation only): required end state and satisfied flag per gold resource."""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODE_DIR))
sys.path.insert(0, str(CODE_DIR / "evaluation"))

import score  # noqa: E402
from ghostaudit.evidence.index import build_ledger  # noqa: E402
from ghostaudit.evidence.vision import vision_observations  # noqa: E402
from ghostaudit.loaders import load_dataset  # noqa: E402
from ghostaudit.pipeline import Context, assess  # noqa: E402

VERIFY_REQUIRED = {"VERIFY_RECORD_ABSENT": "ABSENT", "VERIFY_RECORD_PRESENT": "PRESENT",
                   "VERIFY_RECORD_REDACTED": "REDACTED", "VERIFY_RECORD_ANONYMIZED": "ANONYMIZED",
                   "VERIFY_DATA_FLOW_DISABLED": "DISABLED", "VERIFY_RESTORE_BLOCKED": "BLOCKED"}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=["dev", "holdout", "all"], default="dev")
    args = parser.parse_args(argv)
    dataset = load_dataset(CODE_DIR.parent / "dataset", sample=True)
    ctx = Context(dataset, build_ledger(dataset, extra=vision_observations(dataset, offline=True)))
    gold = score.read_rows(CODE_DIR.parent / "dataset" / "sample_output.csv")
    case_ids = set(score.split_case_ids(args.split, gold))
    counts, flags = Counter(), Counter()
    for request in dataset.requests:
        if request.case_id not in case_ids:
            continue
        assessment = assess(request, ctx)
        flags.update(assessment.flags)
        ours = {o.resource_id: o for o in assessment.policy.obligations}
        gold_required = {s["resource_id"]: VERIFY_REQUIRED[s["operation"]] for s in gold[request.case_id][1]
                         if s["phase"] == "VERIFICATION"}
        gold_violated = {s["resource_id"] for s in gold[request.case_id][1] if s["phase"] == "FINDING"}
        for resource_id, required in sorted(gold_required.items()):
            obligation = ours.get(resource_id)
            if obligation is None:
                counts["gold_obligation_missing"] += 1
                continue
            counts["required_ok" if obligation.required == required else "required_wrong"] += 1
            want_satisfied = resource_id not in gold_violated
            if obligation.current == "UNKNOWN":
                counts["state_unknown"] += 1
            else:
                counts["satisfied_ok" if obligation.satisfied == want_satisfied else "satisfied_wrong"] += 1
            if obligation.required != required or (obligation.current != "UNKNOWN"
                                                   and obligation.satisfied != want_satisfied):
                print(request.case_id, resource_id, "gold", required, "violated" if not want_satisfied else "ok",
                      "| ours", obligation.required, obligation.current, obligation.proof)
        for resource_id in sorted(set(ours) - set(gold_required)):
            counts["extra_obligation"] += 1
            print(request.case_id, "extra", resource_id, ours[resource_id].category, ours[resource_id].required,
                  ours[resource_id].current)
        counts["excluded"] += len(assessment.policy.excluded)
    print(dict(sorted(counts.items())))
    print("flags:", dict(sorted(flags.items())))


if __name__ == "__main__":
    main()
