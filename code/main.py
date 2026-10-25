"""Deletion-audit agent entry point.

python code/main.py [--cases sample|all] [--out PATH] [--offline] [--no-cache] [--case case_NN ...] [--data-root DIR]
                    [--run-manifest-output PATH]
Evaluation-only ablations: [--ablate no-history|trust-claims] [--ungrounded-account-steps ranked]

Candidate first: predictions and diagnostics are written to run-owned staging files, validated, and only then
moved over --out and its diagnostics. A failed generation or validation leaves the previous files untouched.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parent
REPO_ROOT = CODE_DIR.parent
SELECTED_OUTPUT = REPO_ROOT / "output.csv"
CANONICAL_DATA_ROOT = REPO_ROOT / "dataset"
sys.path.insert(0, str(CODE_DIR))

from ghostaudit.evidence.index import build_ledger, trusted_claim_observations  # noqa: E402
from ghostaudit.evidence.vision import vision_observations  # noqa: E402
from ghostaudit.llm.ledger import summarize  # noqa: E402
from ghostaudit.llm.providers import LLMLayer  # noqa: E402
from ghostaudit.loaders import load_dataset  # noqa: E402
from ghostaudit.pipeline import Context, run_case  # noqa: E402
from ghostaudit.provenance import (git_revision, release_configuration_violations, sha256_of,  # noqa: E402
                                   uncommitted_producing_code)
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
    parser.add_argument("--ablate", action="append", choices=["no-history", "trust-claims"], default=[],
                        help="evaluation-only ablation; never used for the submitted output")
    parser.add_argument("--ungrounded-account-steps", choices=["none", "ranked"], default="none",
                        help="evaluation-only ablation: 'ranked' plans the top-ranked guessed account (INCOMPLETE only)")
    parser.add_argument("--run-manifest-output", type=Path, default=None,
                        help="where to write this run's manifest (default runs/<run_id>.manifest.json)")
    return parser.parse_args(argv)


def refuse_non_release_run_targeting_selected_output(args: argparse.Namespace) -> None:
    """Before any data, provider or file work: only the release configuration over the canonical dataset may write
    the selected output.csv. Every other mode stays available with --out elsewhere (spec 0025)."""
    if args.out.resolve() != SELECTED_OUTPUT.resolve():
        return
    violations = release_configuration_violations(vars(args))
    if args.data_root.resolve() != CANONICAL_DATA_ROOT.resolve():
        violations.append(f"--data-root {args.data_root}")
    if violations:
        raise SystemExit(f"refusing to replace the selected {SELECTED_OUTPUT}: not the release configuration "
                         f"({'; '.join(violations)}); pass --out to another path")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    refuse_non_release_run_targeting_selected_output(args)
    run_id = f"{args.out.stem}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    runs_dir = REPO_ROOT / "runs"
    usage_path = runs_dir / f"usage_{run_id}.jsonl"
    dataset = load_dataset(args.data_root, sample=args.cases == "sample")
    llm = LLMLayer(ledger_path=usage_path, offline=args.offline, use_cache=not args.no_cache)
    extra = vision_observations(dataset, layer=llm)
    if "trust-claims" in args.ablate:
        extra += trusted_claim_observations(dataset)
    ledger = build_ledger(dataset, extra=extra)
    ablations = frozenset(args.ablate) | ({"ranked-accounts"} if args.ungrounded_account_steps == "ranked" else set())
    ctx = Context(dataset, ledger, llm=llm, ablations=ablations)
    requests = [r for r in dataset.requests if not args.case or r.case_id in set(args.case)]
    rows, diagnostics = [], []
    for request in requests:
        status, steps, record = run_case(request, ctx)
        rows.append((request.case_id, status, steps))
        diagnostics.append(record)
    diagnostics_path = args.out.with_suffix(".diagnostics.jsonl")
    staged_output = args.out.with_name(f".{args.out.name}.{run_id}.staged")
    staged_diagnostics = diagnostics_path.with_name(f".{diagnostics_path.name}.{run_id}.staged")
    write_output(rows, staged_output)
    staged_diagnostics.write_text("".join(json.dumps(d, sort_keys=True, ensure_ascii=False) + "\n"
                                          for d in diagnostics), encoding="utf-8")
    validation = None
    if not args.case:                     # a partial run cannot satisfy the one-row-per-request rule
        validation = validate_output(staged_output, dataset, staged_diagnostics)
        report(validation)
    published = validation is None or validation.ok
    if published:
        os.replace(staged_diagnostics, diagnostics_path)
        os.replace(staged_output, args.out)
        print(f"wrote {len(rows)} rows to {args.out}; diagnostics {diagnostics_path}")
    else:
        print(f"validation failed: {args.out} left unchanged; rejected candidate kept at {staged_output}")
    final_output, final_diagnostics = (args.out, diagnostics_path) if published else (staged_output, staged_diagnostics)
    manifest = {"run_id": run_id, "git_revision": git_revision(),
                "uncommitted_producing_code": uncommitted_producing_code(),
                "args": vars(args) | {"out": str(args.out), "run_manifest_output": str(args.run_manifest_output)},
                "rows": len(rows), "published": published, "output": str(final_output),
                "output_sha256": sha256_of(final_output), "diagnostics": str(final_diagnostics),
                "diagnostics_sha256": sha256_of(final_diagnostics), "usage_ledger": str(usage_path),
                "usage_ledger_sha256": sha256_of(usage_path) if usage_path.is_file() else None,
                "usage_overall": summarize(llm.ledger.rows)["overall"],
                "validation": None if validation is None else {"errors": len(validation.errors),
                                                               "warnings": len(validation.warnings)}}
    run_manifest_output_path = args.run_manifest_output or runs_dir / f"{run_id}.manifest.json"
    run_manifest_output_path.parent.mkdir(parents=True, exist_ok=True)
    run_manifest_output_path.write_text(json.dumps(manifest, indent=1, sort_keys=True, default=str) + "\n",
                                        encoding="utf-8")
    return 0 if published else 1


if __name__ == "__main__":
    sys.exit(main())
