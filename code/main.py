"""Deletion-audit agent entry point.

python code/main.py [--cases sample|all] [--out PATH] [--offline] [--no-cache] [--case case_NN ...] [--data-root DIR]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parent
REPO_ROOT = CODE_DIR.parent
sys.path.insert(0, str(CODE_DIR))

from ghostaudit.evidence.index import build_ledger  # noqa: E402
from ghostaudit.evidence.vision import vision_observations  # noqa: E402
from ghostaudit.llm.ledger import summarize  # noqa: E402
from ghostaudit.llm.providers import LLMLayer  # noqa: E402
from ghostaudit.loaders import load_dataset  # noqa: E402
from ghostaudit.pipeline import Context, run_case  # noqa: E402
from ghostaudit.serialize import write_output  # noqa: E402
from ghostaudit.validate import report, validate_output  # noqa: E402


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ghost Data Still Exists deletion-audit agent")
    parser.add_argument("--cases", choices=["sample", "all"], default="all")
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "output.csv")
    parser.add_argument("--offline", action="store_true", help="cache-only LLM calls, deterministic fallbacks")
    parser.add_argument("--no-cache", action="store_true", help="skip LLM cache reads (cold run)")
    parser.add_argument("--case", nargs="*", default=None, help="restrict to these case_ids")
    parser.add_argument("--data-root", type=Path, default=REPO_ROOT / "dataset",
                        help="dataset directory (custom evaluation overlays use a temporary copy)")
    return parser.parse_args(argv)


def git_revision() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True,
                              check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    run_id = f"{args.out.stem}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    runs_dir = REPO_ROOT / "runs"
    usage_path = runs_dir / f"usage_{run_id}.jsonl"
    dataset = load_dataset(args.data_root, sample=args.cases == "sample")
    llm = LLMLayer(ledger_path=usage_path, offline=args.offline, use_cache=not args.no_cache)
    ledger = build_ledger(dataset, extra=vision_observations(dataset, layer=llm))
    ctx = Context(dataset, ledger, llm=llm)
    requests = [r for r in dataset.requests if not args.case or r.case_id in set(args.case)]
    rows, diagnostics = [], []
    for request in requests:
        status, steps, record = run_case(request, ctx)
        rows.append((request.case_id, status, steps))
        diagnostics.append(record)
    write_output(rows, args.out)
    diagnostics_path = args.out.with_suffix(".diagnostics.jsonl")
    diagnostics_path.write_text("".join(json.dumps(d, sort_keys=True, ensure_ascii=False) + "\n"
                                        for d in diagnostics), encoding="utf-8")
    print(f"wrote {len(rows)} rows to {args.out}; diagnostics {diagnostics_path}")
    usage = summarize(llm.ledger.rows)["overall"]
    manifest = {"run_id": run_id, "git_revision": git_revision(), "args": vars(args) | {"out": str(args.out)},
                "rows": len(rows), "output_sha256": hashlib.sha256(args.out.read_bytes()).hexdigest(),
                "diagnostics": str(diagnostics_path), "usage_ledger": str(usage_path), "usage_overall": usage}
    runs_dir.mkdir(parents=True, exist_ok=True)
    (runs_dir / f"{run_id}.manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True, default=str))
    if args.case:
        return 0  # a partial run cannot satisfy the one-row-per-request rule
    result = validate_output(args.out, dataset, diagnostics_path)
    report(result)
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
