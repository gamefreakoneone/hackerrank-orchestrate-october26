"""Deletion-audit agent entry point: python code/main.py [--cases sample|all] [--out PATH]."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parent
REPO_ROOT = CODE_DIR.parent
sys.path.insert(0, str(CODE_DIR))

from ghostaudit.loaders import load_dataset  # noqa: E402
from ghostaudit.models import Status  # noqa: E402
from ghostaudit.serialize import write_output  # noqa: E402
from ghostaudit.validate import report, validate_output  # noqa: E402


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
    dataset = load_dataset(REPO_ROOT / "dataset", sample=args.cases == "sample")
    requests = [r for r in dataset.requests if not args.case or r.case_id in set(args.case)]
    rows = [(request.case_id, Status.NOT_APPLICABLE, []) for request in requests]
    write_output(rows, args.out)
    print(f"wrote {len(rows)} rows to {args.out} (format-only baseline)")
    if args.case:
        return 0  # a partial run cannot satisfy the one-row-per-request rule
    result = validate_output(args.out, dataset)
    report(result)
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
