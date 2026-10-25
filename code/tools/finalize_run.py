"""Promote a validated full-run candidate to the selected release (spec 0021). No inference runs here.

python code/tools/finalize_run.py --candidate-manifest runs/corrective/0021_candidate.manifest.json \\
    --evaluation-inputs code/evaluation/corrective_run/evaluation_inputs.json

Checks the candidate (default configuration, committed producing code, hashes, validator with its diagnostics) and the
same-revision evaluation inputs, renders both reports, stages every file, and only then replaces
code/evaluation/final_run/, the reports and output.csv (output last). The replacement is a sequence of renames, not
one atomic operation: an interruption stops with the run id and the location of the previous bundle.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = CODE_DIR.parent
sys.path.insert(0, str(CODE_DIR))
sys.path.insert(0, str(CODE_DIR / "evaluation"))

import make_reports  # noqa: E402
import score  # noqa: E402
from ghostaudit.llm.ledger import load_rows  # noqa: E402
from ghostaudit.loaders import Dataset, load_dataset  # noqa: E402
from ghostaudit.provenance import sha256_of  # noqa: E402
from ghostaudit.validate import validate_output  # noqa: E402

FINAL_RUN_DIRECTORY = "code/evaluation/final_run"
REPORT_NAMES = ("evaluation_report.md", "usage_report.md")


def fail(message: str) -> None:
    raise SystemExit(f"finalize_run: {message}")


def checked_candidate_files(candidate: dict, dataset: Dataset, repository_root: Path) -> dict[str, Path]:
    """The candidate must be the published default configuration of committed code, intact and valid."""
    args = candidate["args"]
    if args.get("case"):
        fail(f"candidate {candidate['run_id']} is a --case subset, not a full run")
    if args.get("ablate") or args.get("ungrounded_account_steps") != "none" or args.get("offline"):
        fail(f"candidate {candidate['run_id']} is not the default configuration: {args}")
    if candidate.get("uncommitted_producing_code") != []:
        fail(f"candidate {candidate['run_id']} ran uncommitted producing code: {candidate.get('uncommitted_producing_code')}")
    if not candidate.get("published"):
        fail(f"candidate {candidate['run_id']} failed its own validation and was not published")
    files = {role: repository_root / candidate[role] for role in ("output", "diagnostics", "usage_ledger")}
    for role, path in files.items():
        if not path.is_file():
            fail(f"candidate {role} is missing: {path}")
        if sha256_of(path) != candidate[f"{role}_sha256"]:
            fail(f"candidate {role} {path} does not match its recorded sha256")
    validation = validate_output(files["output"], dataset, files["diagnostics"])
    if not validation.ok:
        fail(f"candidate fails validation with its diagnostics: {validation.errors[:5]}")
    return files


def finalize(candidate_manifest_path: Path, evaluation_inputs_path: Path, repository_root: Path = REPO_ROOT,
             dataset: Dataset | None = None) -> dict:
    if not candidate_manifest_path.is_file():
        fail(f"candidate manifest is missing: {candidate_manifest_path}")
    candidate = json.loads(candidate_manifest_path.read_text(encoding="utf-8"))
    files = checked_candidate_files(candidate, dataset or load_dataset(repository_root / "dataset"), repository_root)
    gold = score.read_rows(repository_root / "dataset" / "sample_output.csv")
    inputs = make_reports.load_evaluation_inputs(evaluation_inputs_path, gold)
    if inputs["code_revision"] != candidate["git_revision"]:
        fail(f"evaluation inputs revision {inputs['code_revision']} != candidate revision {candidate['git_revision']}; "
             "capture the evaluation inputs from the same frozen code")
    run_id = candidate["run_id"]
    selected_manifest = {
        "run_id": run_id, "git_revision": candidate["git_revision"], "args": candidate["args"],
        "rows": candidate["rows"], "output_sha256": candidate["output_sha256"],
        "diagnostics": f"{FINAL_RUN_DIRECTORY}/diagnostics.jsonl", "diagnostics_sha256": candidate["diagnostics_sha256"],
        "usage_ledger": f"{FINAL_RUN_DIRECTORY}/usage_ledger.jsonl",
        "usage_ledger_sha256": candidate["usage_ledger_sha256"], "usage_overall": candidate["usage_overall"],
        "validation": candidate["validation"],
        "evaluation_inputs": evaluation_inputs_path.resolve().relative_to(repository_root.resolve()).as_posix(),
        "original_paths": {"manifest": str(candidate_manifest_path), "output": candidate["output"],
                           "diagnostics": candidate["diagnostics"], "usage_ledger": candidate["usage_ledger"]},
        "promoted_to": "output.csv (repository root)"}
    final = {"manifest": selected_manifest, "output": files["output"],
             "diagnostics": score.read_diagnostics(files["diagnostics"]), "usage_rows": load_rows(files["usage_ledger"])}
    reports = {"evaluation_report.md": make_reports.evaluation_report(final, inputs, gold, unified=True),
               "usage_report.md": make_reports.usage_report(final)}

    staging = repository_root / f".finalize_{run_id}"
    shutil.rmtree(staging, ignore_errors=True)
    (staging / "final_run").mkdir(parents=True)
    shutil.copyfile(files["diagnostics"], staging / "final_run" / "diagnostics.jsonl")
    shutil.copyfile(files["usage_ledger"], staging / "final_run" / "usage_ledger.jsonl")
    (staging / "final_run" / "manifest.json").write_text(json.dumps(selected_manifest, indent=1, sort_keys=True) + "\n",
                                                         encoding="utf-8")
    for name, text in reports.items():
        (staging / name).write_text(text, encoding="utf-8")
    shutil.copyfile(files["output"], staging / "output.csv")

    final_run_directory = repository_root / FINAL_RUN_DIRECTORY
    previous = final_run_directory.with_name(f"final_run.previous_{run_id}")
    try:
        if final_run_directory.exists():
            os.replace(final_run_directory, previous)
        os.replace(staging / "final_run", final_run_directory)
        for name in REPORT_NAMES:
            os.replace(staging / name, final_run_directory.parent / name)
        os.replace(staging / "output.csv", repository_root / "output.csv")
    except OSError as error:
        fail(f"publication of {run_id} was interrupted ({error}); previous final_run kept at {previous}, staged files "
             f"at {staging}; the last committed release is the recovery point")
    published = make_reports.load_final_run(final_run_directory / "manifest.json", repository_root)
    for role in ("diagnostics", "usage_ledger"):
        if sha256_of(repository_root / selected_manifest[role]) != selected_manifest[f"{role}_sha256"]:
            fail(f"published {role} does not match the candidate's sha256")
    rerendered = {"evaluation_report.md": make_reports.evaluation_report(published, inputs, gold, unified=True),
                  "usage_report.md": make_reports.usage_report(published)}
    if any((final_run_directory.parent / name).read_text(encoding="utf-8") != text for name, text in rerendered.items()):
        fail("published reports differ from a re-render of the published bundle")
    shutil.rmtree(previous, ignore_errors=True)
    shutil.rmtree(staging, ignore_errors=True)
    return selected_manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--candidate-manifest", type=Path, required=True)
    parser.add_argument("--evaluation-inputs", type=Path, required=True)
    args = parser.parse_args(argv)
    manifest = finalize(args.candidate_manifest, args.evaluation_inputs)
    print(f"selected run {manifest['run_id']} (code {manifest['git_revision']}, output sha256 "
          f"{manifest['output_sha256']}) published to output.csv and {FINAL_RUN_DIRECTORY}/ with both reports")
    return 0


if __name__ == "__main__":
    sys.exit(main())
