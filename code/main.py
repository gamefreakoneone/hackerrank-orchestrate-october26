"""Deletion-audit agent entry point: python code/main.py [--cases sample|all] [--out PATH]."""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parent
REPO_ROOT = CODE_DIR.parent
sys.path.insert(0, str(CODE_DIR))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ghost Data Still Exists deletion-audit agent")
    parser.add_argument("--cases", choices=["sample", "all"], default="all")
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "output.csv")
    parser.add_argument("--offline", action="store_true", help="cache-only LLM calls, deterministic fallbacks")
    parser.add_argument("--no-cache", action="store_true", help="bypass the LLM and evidence caches")
    parser.add_argument("--case", nargs="*", default=None, help="restrict to these case_ids")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    requests_file = "sample_deletion_requests.csv" if args.cases == "sample" else "deletion_requests.csv"
    with (REPO_ROOT / "dataset" / requests_file).open(encoding="utf-8-sig", newline="") as handle:
        requests = list(csv.DictReader(handle))
    if args.case:
        requests = [r for r in requests if r["case_id"] in set(args.case)]
    requests.sort(key=lambda r: int(r["case_id"].split("_")[1]))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["case_id", "deletion_status", "steps_json"])
        for request in requests:
            writer.writerow([request["case_id"], "NOT_APPLICABLE", "[]"])
    print(f"wrote {len(requests)} rows to {args.out} (format-only baseline)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
