"""Spec 0021: a freshly built code.zip of this tree is a runnable, consistent release on its own — required files,
no dataset/secrets/caches, the selected manifest matches output.csv, and in a clean room (extracted archive + dataset
+ output.csv, nothing else) the reports rebuild byte-identically without model calls and an offline sample run passes.
Release-stage check: it needs the finalized bundle, so the pre-finalization evaluation capture does not run it."""
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "code" / "tools"))

import make_zip  # noqa: E402
from ghostaudit.provenance import sha256_of  # noqa: E402

REQUIRED_FILES = {"README.md", "main.py", "requirements.txt", "evaluation/evaluation_report.md",
                  "evaluation/usage_report.md", "evaluation/final_run/manifest.json", "evaluation/make_reports.py"}
FORBIDDEN_PARTS = {"dataset", ".cache", "runs", "__pycache__", ".pytest_cache"}


@pytest.fixture(scope="module")
def clean_room(tmp_path_factory):
    work = tmp_path_factory.mktemp("package")
    archive_path = work / "code.zip"
    assert make_zip.main(["--output", str(archive_path)]) == 0                  # a new build, not an old file
    room = work / "clean"
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        archive.extractall(room / "code")
    (room / "dataset").symlink_to(REPO_ROOT / "dataset", target_is_directory=True)
    (room / "output.csv").write_bytes((REPO_ROOT / "output.csv").read_bytes())
    return room, names


def run(command: list[str], room: Path) -> subprocess.CompletedProcess:
    environment = {k: v for k, v in os.environ.items() if not any(t in k for t in ("API_KEY", "ENDPOINT", "API_BASE"))}
    return subprocess.run(command, cwd=room, capture_output=True, text=True, env=environment)


def test_archive_layout_and_exclusions(clean_room):
    _, names = clean_room
    assert REQUIRED_FILES <= set(names)
    assert not [n for n in names if set(Path(n).parts) & FORBIDDEN_PARTS or Path(n).name == ".env"
                or n.endswith((".zip", ".pyc"))]


def test_selected_manifest_matches_the_selected_output(clean_room):
    room, _ = clean_room
    manifest = json.loads((room / "code" / "evaluation" / "final_run" / "manifest.json").read_text())
    assert manifest["output_sha256"] == sha256_of(room / "output.csv")
    for role in ("diagnostics", "usage_ledger"):
        assert sha256_of(room / manifest[role]) == manifest[f"{role}_sha256"]


def test_reports_rebuild_identically_in_the_clean_room(clean_room):
    room, _ = clean_room
    completed = run([sys.executable, "code/evaluation/make_reports.py", "--report-output-directory", "rebuilt"], room)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    for name in ("evaluation_report.md", "usage_report.md"):
        assert (room / "rebuilt" / name).read_bytes() == (room / "code" / "evaluation" / name).read_bytes()


def test_offline_sample_run_works_from_the_extracted_layout(clean_room):
    room, _ = clean_room
    completed = run([sys.executable, "code/main.py", "--cases", "sample", "--offline", "--out", "sample.csv"], room)
    assert completed.returncode == 0, completed.stdout[-2000:] + completed.stderr[-2000:]
    assert len((room / "sample.csv").read_text().splitlines()) == 33
