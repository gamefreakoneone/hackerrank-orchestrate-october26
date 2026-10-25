"""Capture the evaluation inputs that make_reports.py renders, with hashes and the producing code revision.

python code/evaluation/capture_inputs.py [--bundle-directory code/evaluation/corrective_run]

Runs the sample configurations, the custom cases, the discovery report and the test suites at a clean, committed
code revision, copies their outputs into the bundle and writes evaluation_inputs.json. Model calls happen here
(cached where the cache holds them), never in make_reports.py.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

EVALUATION_DIR = Path(__file__).resolve().parent
CODE_DIR = EVALUATION_DIR.parent
REPO_ROOT = CODE_DIR.parent
DEFAULT_BUNDLE_DIRECTORY = EVALUATION_DIR / "corrective_run"
EVALUATION_INPUTS_FILE = "evaluation_inputs.json"
# name -> main.py flags; "default" is the submitted configuration, the others are evaluation-only ablations
SAMPLE_CONFIGURATIONS: dict[str, list[str]] = {
    "default": [],
    "deterministic": ["--offline", "--no-cache"],
    "no-history": ["--ablate", "no-history"],
    "trust-claims": ["--ablate", "trust-claims"],
    "ranked-accounts": ["--ungrounded-account-steps", "ranked"],
}
TEST_COMMANDS = {"full_suite": ["code/tests"], "metamorphic": ["code/tests/test_metamorphic.py"]}
PROVIDER_ENVIRONMENT_VARIABLES = ("TYPESAFE_API_KEY", "AZURE_OPENAI_API_KEY", "GEMINI_API_KEY")


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*arguments: str) -> str:
    return subprocess.run(["git", *arguments], cwd=REPO_ROOT, capture_output=True, text=True, check=True).stdout


def require_committed_code(bundle_directory: Path) -> str:
    """The recorded revision must be the code that ran: no uncommitted change under code/ outside the bundle."""
    bundle_relative = bundle_directory.resolve().relative_to(REPO_ROOT).as_posix()
    dirty = [line for line in git("status", "--porcelain", "--", "code").splitlines()
             if bundle_relative not in line]
    if dirty:
        raise SystemExit("capture needs committed code; uncommitted changes under code/:\n" + "\n".join(dirty))
    return git("rev-parse", "HEAD").strip()


def run_sample_configuration(name: str, flags: list[str], bundle_directory: Path) -> dict:
    predictions = bundle_directory / f"sample_{name}.csv"
    command = [sys.executable, str(CODE_DIR / "main.py"), "--cases", "sample", "--out", str(predictions), *flags]
    completed = subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True)
    if completed.returncode != 0:
        raise SystemExit(f"sample configuration {name!r} failed ({completed.returncode}):\n{completed.stdout[-2000:]}"
                         f"\n{completed.stderr[-2000:]}")
    run_manifest = max((REPO_ROOT / "runs").glob(f"{predictions.stem}_*.manifest.json"), key=lambda p: p.name)
    diagnostics = predictions.with_suffix(".diagnostics.jsonl")
    return {"pipeline_args": flags, "predictions": predictions.name, "predictions_sha256": sha256_of(predictions),
            "diagnostics": diagnostics.name, "diagnostics_sha256": sha256_of(diagnostics),
            "model_calls": json.loads(run_manifest.read_text(encoding="utf-8"))["usage_overall"]}


def run_tests(name: str, targets: list[str]) -> dict:
    environment = {k: v for k, v in os.environ.items() if k != "RUN_LIVE"}
    command = [sys.executable, "-m", "pytest", *targets, "-q"]
    completed = subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True, env=environment)
    summary = (completed.stdout.strip().splitlines() or ["(no output)"])[-1].split(" in ")[0]
    return {"name": name, "command": "python -m pytest " + " ".join(targets) + " -q",
            "exit_code": completed.returncode, "summary": summary}


def copy_into_bundle(source: Path, bundle_directory: Path, name: str) -> dict:
    if not source.is_file():
        raise SystemExit(f"expected {source} to exist after its producing command")
    shutil.copyfile(source, bundle_directory / name)
    return {"path": name, "sha256": sha256_of(bundle_directory / name)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-directory", type=Path, default=DEFAULT_BUNDLE_DIRECTORY)
    args = parser.parse_args(argv)
    bundle_directory = args.bundle_directory.resolve()
    code_revision = require_committed_code(bundle_directory)
    if bundle_directory.exists():
        shutil.rmtree(bundle_directory)
    bundle_directory.mkdir(parents=True)
    llm_cache = CODE_DIR / ".cache" / "llm"
    inputs = {
        "code_revision": code_revision,
        "captured_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "provider_configuration": {
            "provider_keys_present": [k for k in PROVIDER_ENVIRONMENT_VARIABLES if os.environ.get(k)],
            "llm_cache_entries_before_capture": len(list(llm_cache.glob("*.json"))) if llm_cache.is_dir() else 0},
        "sample_runs": {name: run_sample_configuration(name, flags, bundle_directory)
                        for name, flags in SAMPLE_CONFIGURATIONS.items()},
    }
    custom = subprocess.run([sys.executable, str(EVALUATION_DIR / "run_custom.py")], cwd=REPO_ROOT,
                            capture_output=True, text=True)
    inputs["custom_results"] = {**copy_into_bundle(REPO_ROOT / "runs" / "custom" / "results.json", bundle_directory,
                                                   "custom_results.json"), "exit_code": custom.returncode}
    discovery = bundle_directory / "discovery.json"
    subprocess.run([sys.executable, str(CODE_DIR / "tools" / "discovery_report.py"), "--split", "all", "--out",
                    str(discovery)], cwd=REPO_ROOT, capture_output=True, text=True, check=True)
    inputs["discovery_report"] = {"path": discovery.name, "sha256": sha256_of(discovery)}
    inputs["test_results"] = [run_tests(name, targets) for name, targets in TEST_COMMANDS.items()]
    (bundle_directory / EVALUATION_INPUTS_FILE).write_text(json.dumps(inputs, indent=1, sort_keys=True) + "\n",
                                                           encoding="utf-8")
    print(f"wrote {bundle_directory / EVALUATION_INPUTS_FILE} at revision {code_revision}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
