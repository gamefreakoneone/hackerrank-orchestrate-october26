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
from ghostaudit.timeline import (delete_claim_times, exposed_direct_identifiers, has_user_link,  # noqa: E402
                                 last_delete_before, resource_category, state_at)


def reconstructed(ops: set[str], state, subject) -> tuple[str | None, str | None]:
    if "VERIFY_DATA_FLOW_DISABLED" in ops:
        fact = state.enabled
        return (None, None) if fact is None else ("VIOLATED" if fact.value else "OK", fact.proof)
    if "VERIFY_RESTORE_BLOCKED" in ops:
        fact = state.restorable
        return (None, None) if fact is None else ("VIOLATED" if fact.value else "OK", fact.proof)
    fact = state.presence
    if fact is None:
        return None, None
    if ops & {"VERIFY_RECORD_REDACTED", "VERIFY_RECORD_ANONYMIZED"}:
        if fact.value == "absent":
            return "OK", fact.proof
        exposed = exposed_direct_identifiers(fact.observation, subject)
        linked = "VERIFY_RECORD_ANONYMIZED" in ops and has_user_link(fact.observation, subject)
        return ("VIOLATED" if exposed or linked else "OK"), fact.proof
    if "VERIFY_RECORD_PRESENT" in ops:
        return ("OK" if fact.value == "present" else "VIOLATED"), fact.proof
    return ("VIOLATED" if fact.value == "present" else "OK"), fact.proof


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
            state = state_at(resource_id, system_id, resource_category(resource_id, request.audit_at, ledger),
                             request.audit_at, ledger, last_delete_before(deletes, resource_id, request.audit_at))
            got, proof = reconstructed(ops, state, subject)
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
