"""State agreement on the sample gold resources (evaluation only: reads sample_output.csv).

For every gold (system, resource) the expected state is "violated" when gold reports a finding for it and
"compliant" otherwise; the reconstructed state at audit_at and its proof are compared with gold.
"""
from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODE_DIR))
sys.path.insert(0, str(CODE_DIR / "evaluation"))

import score  # noqa: E402
from ghostaudit.evidence.index import build_ledger  # noqa: E402
from ghostaudit.evidence.vision import vision_observations  # noqa: E402
from ghostaudit.identity import resolve  # noqa: E402
from ghostaudit.loaders import load_dataset  # noqa: E402
from ghostaudit.obligations import build_obligation, treatment_violated  # noqa: E402
from ghostaudit.timeline import delete_claim_times, last_delete_before, resource_category, state_at  # noqa: E402


VERIFY_REQUIRED = {"VERIFY_DATA_FLOW_DISABLED": "DISABLED", "VERIFY_RESTORE_BLOCKED": "BLOCKED",
                   "VERIFY_RECORD_REDACTED": "REDACTED", "VERIFY_RECORD_ANONYMIZED": "ANONYMIZED",
                   "VERIFY_RECORD_PRESENT": "PRESENT", "VERIFY_RECORD_ABSENT": "ABSENT"}


def reconstructed(ops: set[str], state, subject, category: str | None) -> tuple[str | None, str | None]:
    """Gold's verification operation names the required state; the engine's own obligation evaluation decides it.
    MISSING = a kept record that is not preserved (no finding can express it)."""
    required = next(VERIFY_REQUIRED[op] for op in VERIFY_REQUIRED if op in ops)
    obligation = build_obligation(system_id="", resource_id=state.resource_id, category=category or "",
                                  required=required, condition="TRUE", state=state, subject=subject,
                                  preservation_required=required not in ("ABSENT", "DISABLED"))
    if obligation.current == "UNKNOWN":
        return None, None
    verdict = "VIOLATED" if treatment_violated(obligation) else "OK" if obligation.satisfied else "MISSING"
    return verdict, obligation.proof


def main() -> None:
    dataset = load_dataset(CODE_DIR.parent / "dataset", sample=True)
    ledger = build_ledger(dataset, extra=vision_observations(dataset, offline=True))
    gold = score.read_rows(CODE_DIR.parent / "dataset" / "sample_output.csv")
    deletes = delete_claim_times(dataset.activity)
    counts = Counter()
    for request in dataset.requests:
        subject = resolve(request, dataset)
        steps_by_resource = defaultdict(list)
        for step in gold[request.case_id][1]:
            steps_by_resource[(step["system_id"], step["resource_id"])].append(step)
        for (system_id, resource_id), steps in sorted(steps_by_resource.items()):
            ops = {s["operation"] for s in steps}
            category = resource_category(resource_id, request.audit_at, ledger)
            state = state_at(resource_id, system_id, category, request.audit_at, ledger,
                             last_delete_before(deletes, resource_id, request.audit_at), subject.user_id)
            got, proof = reconstructed(ops, state, subject, category)
            want = "VIOLATED" if any(s["phase"] == "FINDING" for s in steps) else "OK"
            cited = {s["evidence_id"] for s in steps if s["evidence_id"]}
            counts["state_ok" if got == want else "state_unknown" if got is None else "state_wrong"] += 1
            if cited:
                counts["proof_matches_gold" if got == want and proof in cited else "proof_differs"] += 1
            if got != want or (cited and proof not in cited):
                print(request.case_id, resource_id, "want", want, "got", got, "proof", proof, "gold", sorted(cited))
    print(dict(counts))


if __name__ == "__main__":
    main()
