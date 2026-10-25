"""Intent decisions of a run: labels, sources, keyword disagreements and CLASSIFY_REQUEST cross-check.

python code/tools/intent_report.py [DIAGNOSTICS]   (default runs/all.diagnostics.jsonl)
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    path = Path(argv[0]) if argv else REPO_ROOT / "runs" / "all.diagnostics.jsonl"
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    labels = Counter((r["intent"]["label"], r["intent"]["source"]) for r in records)
    print(f"{len(records)} requests; label/source: {dict(sorted(labels.items()))}")
    keyword_disagreements = [r for r in records if (r["intent"]["label"] == "DELETION") != r["intent"]["keyword_deletion"]]
    print(f"keyword disagreements (resolved by the model decision table): {len(keyword_disagreements)}")
    for r in keyword_disagreements:
        print(f"  {r['case_id']}: final {r['intent']['label']} via {r['intent']['source']}, jev {r['intent']['jev_label']}, "
              f"keyword deletion={r['intent']['keyword_deletion']}")
    crosscheck = [r for r in records if r.get("classify_request_non_deletion")]
    print(f"CLASSIFY_REQUEST non-deletion on the subject's grounded account (cross-check only): {len(crosscheck)}")
    for r in crosscheck:
        print(f"  {r['case_id']}: final {r['intent']['label']}; activities {r['classify_request_non_deletion']}")


if __name__ == "__main__":
    main()
