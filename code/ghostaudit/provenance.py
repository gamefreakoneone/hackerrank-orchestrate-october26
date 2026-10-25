"""Run provenance shared by the pipeline, the evaluation capture and the release finalizer: code revision,
uncommitted producing code, artifact hashes and the release configuration. No model or provider imports."""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
# Files whose content determines predictions and evaluation results (artifacts and documentation excluded).
PRODUCING_CODE_PATHSPECS = ("code/main.py", "code/ghostaudit", "code/config", "code/prompts", "code/requirements.txt",
                            "code/evaluation/*.py", "code/evaluation/cases", "code/evaluation/split.json", "code/tools")


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_revision() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True,
                              check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def uncommitted_producing_code() -> list[str]:
    """Uncommitted changes to the producing code; non-empty means git_revision() is not the code that ran."""
    try:
        return subprocess.run(["git", "status", "--porcelain", "--", *PRODUCING_CODE_PATHSPECS], cwd=REPO_ROOT,
                              capture_output=True, text=True, check=True).stdout.splitlines()
    except (OSError, subprocess.CalledProcessError):
        return ["(git unavailable)"]


def release_configuration_violations(run_args: dict) -> list[str]:
    """Why a run's arguments are not the release configuration (all requests, default inference); [] = release.
    --no-cache is a cache policy, not an ablation. Shared by main.py's selected-output guard and finalize_run."""
    violations = []
    if run_args.get("cases") != "all":
        violations.append(f"--cases {run_args.get('cases')}")
    if run_args.get("case") is not None:
        violations.append(f"--case selector {run_args['case']}")
    if run_args.get("ablate"):
        violations.append(f"--ablate {' '.join(run_args['ablate'])}")
    if run_args.get("ungrounded_account_steps") != "none":
        violations.append(f"--ungrounded-account-steps {run_args.get('ungrounded_account_steps')}")
    if run_args.get("offline"):
        violations.append("--offline")
    return violations
