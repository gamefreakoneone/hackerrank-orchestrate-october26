"""Per-file evidence coverage report: observations / coverage rows, or the reason a file yields none."""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODE_DIR))

from ghostaudit.evidence.index import build_ledger  # noqa: E402
from ghostaudit.loaders import load_dataset  # noqa: E402


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--png", action="store_true", help="include vision extraction (spec 0009)")
    args = parser.parse_args(argv)
    dataset = load_dataset(CODE_DIR.parent / "dataset")
    extra = []
    if args.png:
        from ghostaudit.evidence.vision import vision_observations
        extra = vision_observations(dataset, offline=True)
    ledger = build_ledger(dataset, extra=extra)
    observations_per_file = Counter(o.evidence_id for o in ledger.observations)
    coverage_per_file = Counter(c.file_id for c in ledger.coverage)
    print("| file | kind | origin | observations | coverage rows | note |")
    print("|---|---|---|---|---|---|")
    for file_id, evidence_file in sorted(dataset.evidence.items(), key=lambda kv: int(kv[0].split("_")[1])):
        print(f"| {file_id} | {Path(evidence_file.file_path).suffix[1:]} | {evidence_file.origin} | "
              f"{observations_per_file[file_id]} | {coverage_per_file[file_id]} | "
              f"{ledger.empty_files.get(file_id, '')} |")
    kinds = Counter(o.source_kind for o in ledger.observations)
    print(f"\ntotal observations {len(ledger.observations)} {dict(sorted(kinds.items()))}; "
          f"coverage rows {len(ledger.coverage)}; files without records {len(ledger.empty_files)}")


if __name__ == "__main__":
    main()
