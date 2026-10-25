"""Build code.zip from the tracked files under code/ (zip root = the code/ folder's contents).

Excludes .env, caches, runs/, __pycache__, nested archives and anything under dataset/; requires both evaluation
reports; fails if any file contains a key-like string or the value of a provider credential from the environment.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT = REPO_ROOT / "code.zip"
REQUIRED = ("evaluation/evaluation_report.md", "evaluation/usage_report.md", "README.md", "main.py",
            "requirements.txt")
EXCLUDED_PARTS = {".cache", "runs", "__pycache__", "dataset", ".pytest_cache"}
SECRET_PATTERNS = [re.compile(p) for p in (
    r"sk-[A-Za-z0-9_-]{20,}", r"AIza[0-9A-Za-z_-]{30,}", r"Bearer [A-Za-z0-9._-]{20,}",
    r"(?i)(api[_-]?key|secret|password|access[_-]?token)[ \t]*[:=][ \t]*['\"]?[A-Za-z0-9_\-+/]{16,}")]
CREDENTIAL_ENV_VARS = ("TYPESAFE_API_KEY", "AZURE_OPENAI_API_KEY", "GEMINI_API_KEY", "AZURE_OPENAI_ENDPOINT")


def tracked_code_files() -> list[Path]:
    listing = subprocess.run(["git", "ls-files", "code/"], cwd=REPO_ROOT, capture_output=True, text=True, check=True)
    files = []
    for line in sorted(listing.stdout.splitlines()):
        relative = Path(line).relative_to("code")
        if set(relative.parts) & EXCLUDED_PARTS or relative.name == ".env" or relative.suffix in (".zip", ".pyc"):
            continue
        files.append(relative)
    return files


def secret_findings(name: str, data: bytes) -> list[str]:
    text = data.decode("utf-8", errors="ignore")
    findings = [f"{name}: matches {pattern.pattern[:20]}…" for pattern in SECRET_PATTERNS if pattern.search(text)]
    for variable in CREDENTIAL_ENV_VARS:
        value = os.environ.get(variable, "").strip()
        if len(value) >= 8 and value in text:
            findings.append(f"{name}: contains the value of ${variable}")
    return findings


def main() -> int:
    files = tracked_code_files()
    missing = [r for r in REQUIRED if Path(r) not in files]
    if missing:
        print(f"missing required files: {missing}")
        return 1
    findings = []
    with zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for relative in files:
            data = (REPO_ROOT / "code" / relative).read_bytes()
            findings += secret_findings(str(relative), data)
            info = zipfile.ZipInfo(relative.as_posix(), date_time=(2026, 10, 25, 0, 0, 0))   # deterministic
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
    if findings:
        OUTPUT.unlink()
        print("secret scan failed:\n" + "\n".join(findings))
        return 1
    print(f"wrote {OUTPUT.name}: {len(files)} files, {OUTPUT.stat().st_size} bytes; secret scan clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
