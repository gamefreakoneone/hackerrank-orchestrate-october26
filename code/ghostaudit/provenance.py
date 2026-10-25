"""Run provenance shared by the pipeline, the evaluation capture and the release finalizer: code revision,
uncommitted producing code and artifact hashes. No model or provider imports."""
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
