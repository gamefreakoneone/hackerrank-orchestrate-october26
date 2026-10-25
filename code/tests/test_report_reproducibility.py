"""Spec 0020: reports rebuild from a preserved fictional bundle through the real CLI, without runs/, caches,
credentials or model access; missing or mismatched inputs fail explicitly; staging leaves selected reports alone."""
import csv
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

CODE_DIR = Path(__file__).resolve().parents[1]
MAKE_REPORTS = CODE_DIR / "evaluation" / "make_reports.py"
SPLIT = json.loads((CODE_DIR / "evaluation" / "split.json").read_text())
SAMPLE_CASE_IDS = sorted(SPLIT["dev"] + SPLIT["holdout"], key=lambda c: int(c.split("_")[1]))
GROUNDED = SAMPLE_CASE_IDS[:4]                    # 4 grounded samples ...
NOT_EXACT = set(SAMPLE_CASE_IDS[2:4])             # ... of which 2 lack one step (not exact)
CODE_REVISION = "f" * 40


def account_plan(case_id: str) -> list[dict]:
    account = f"account_{case_id.split('_')[1]}"
    rows = [("FINDING", "REPORT_REMAINING_RECORD", "PRESENT", "evidence_01"),
            ("REMEDIATION", "DELETE_RECORD", "ABSENT", ""), ("VERIFICATION", "VERIFY_RECORD_ABSENT", "ABSENT", "")]
    return [{"step_no": n, "phase": phase, "system_id": "account_service", "resource_id": account, "operation": op,
             "state": state, "evidence_id": evidence} for n, (phase, op, state, evidence) in enumerate(rows, start=1)]


def write_csv(path: Path, rows: list[tuple[str, str, list]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["case_id", "deletion_status", "steps_json"])
        writer.writerows([case_id, status, json.dumps(steps)] for case_id, status, steps in rows)


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def bundle(tmp_path):
    root = tmp_path / "repo"
    write_csv(root / "dataset" / "sample_output.csv", [(c, "INCOMPLETE", account_plan(c)) for c in SAMPLE_CASE_IDS])
    write_csv(root / "output.csv", [("case_1", "INCOMPLETE", account_plan("case_1")), ("case_2", "NOT_APPLICABLE", [])])
    final = root / "code" / "evaluation" / "final_run"
    write_jsonl(final / "diagnostics.jsonl", [{"case_id": "case_1", "flags": ["ACCOUNT_UNGROUNDED"],
                                               "account_link": {"via": "ungrounded"}},
                                              {"case_id": "case_2", "flags": []}])
    write_jsonl(final / "usage_ledger.jsonl", [
        {"provider": "jev", "model": "jev-1.14.0", "task": "intent", "input_tokens": 1234, "output_tokens": 5,
         "cached": False, "attempts": 1, "latency_ms": 1}])
    manifest = {"run_id": "fixture_run", "git_revision": CODE_REVISION, "rows": 2,
                "output_sha256": sha256_of(root / "output.csv"), "args": {"cases": "all", "no_cache": True},
                "diagnostics": "code/evaluation/final_run/diagnostics.jsonl",
                "diagnostics_sha256": sha256_of(final / "diagnostics.jsonl"),
                "usage_ledger": "code/evaluation/final_run/usage_ledger.jsonl",
                "usage_ledger_sha256": sha256_of(final / "usage_ledger.jsonl"),
                "evaluation_inputs": "code/evaluation/fixture_bundle/evaluation_inputs.json"}
    write_final_manifest(root, manifest)
    inputs_dir = root / "code" / "evaluation" / "fixture_bundle"
    predictions = [(c, "INCOMPLETE", account_plan(c)[:2] if c in NOT_EXACT else account_plan(c))
                   for c in SAMPLE_CASE_IDS]
    write_csv(inputs_dir / "sample_default.csv", predictions)
    write_jsonl(inputs_dir / "sample_default.diagnostics.jsonl", [
        {"case_id": c, "flags": [] if c in GROUNDED else ["ACCOUNT_UNGROUNDED"],
         "account_link": {"via": "grounded", "current": f"account_{c.split('_')[1]}"} if c in GROUNDED
         else {"via": "ungrounded", "current": None}} for c in SAMPLE_CASE_IDS])
    custom = {"offline": False, "results": [
        {"case": "synthetic_one", "case_id": "case_9001", "expected_status": "COMPLETE", "got_status": "COMPLETE",
         "status_ok": True, "steps_ok": True, "flags_ok": True, "validator_ok": True, "flags": []},
        {"case": "synthetic_two", "case_id": "case_9002", "expected_status": "INCOMPLETE", "got_status": "COMPLETE",
         "status_ok": False, "steps_ok": False, "flags_ok": True, "validator_ok": True, "flags": []}]}
    (inputs_dir / "custom_results.json").write_text(json.dumps(custom), encoding="utf-8")
    inputs = {"code_revision": CODE_REVISION, "captured_at": "2026-10-25T00:00:00Z",
              "provider_configuration": {"provider_keys_present": [], "llm_cache_entries_before_capture": 0},
              "sample_runs": {"default": {"pipeline_args": [], "predictions": "sample_default.csv",
                                          "predictions_sha256": sha256_of(inputs_dir / "sample_default.csv"),
                                          "diagnostics": "sample_default.diagnostics.jsonl",
                                          "diagnostics_sha256": sha256_of(inputs_dir / "sample_default.diagnostics.jsonl"),
                                          "model_calls": {"calls": 0, "cached_calls": 32}}},
              "custom_results": {"path": "custom_results.json", "sha256": sha256_of(inputs_dir / "custom_results.json")},
              "test_results": [{"name": "full_suite", "command": "python -m pytest code/tests -q", "exit_code": 0,
                                "summary": "7 passed"}]}
    write_inputs(inputs_dir, inputs)
    return root, inputs_dir, inputs


FINAL_RUN = Path("code") / "evaluation" / "final_run"


def write_final_manifest(root: Path, manifest: dict) -> None:
    (root / FINAL_RUN / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def read_final_manifest(root: Path) -> dict:
    return json.loads((root / FINAL_RUN / "manifest.json").read_text(encoding="utf-8"))


def write_inputs(inputs_dir: Path, inputs: dict) -> None:
    (inputs_dir / "evaluation_inputs.json").write_text(json.dumps(inputs), encoding="utf-8")


def make_reports(root: Path, *extra: str, output_directory: str = "staged") -> subprocess.CompletedProcess:
    """The real CLI in a fresh process: no provider credentials, an unusable proxy, cwd without runs/."""
    environment = {k: v for k, v in os.environ.items()
                   if not any(t in k for t in ("API_KEY", "ENDPOINT", "API_BASE", "PROXY", "proxy"))}
    environment["HTTPS_PROXY"] = environment["HTTP_PROXY"] = "http://127.0.0.1:9"
    probe = ("import runpy, sys; sys.argv = sys.argv[1:]; "
             "exit_code = 0\ntry:\n    runpy.run_path(sys.argv[0], run_name='__main__')\n"
             "except SystemExit as stop:\n    exit_code = stop.code if isinstance(stop.code, int) else 1\n"
             "    print(stop, file=sys.stderr)\n"
             "print('provider modules loaded:', sorted(m for m in sys.modules if m.startswith(('strands', "
             "'typesafe_sdk', 'openai', 'google.genai', 'ghostaudit.llm.providers'))))\nsys.exit(exit_code)")
    command = [sys.executable, "-c", probe, str(MAKE_REPORTS), "--repository-root", str(root),
               "--final-manifest", str(root / "code" / "evaluation" / "final_run" / "manifest.json"),
               "--report-output-directory", str(root / output_directory), *extra]
    return subprocess.run(command, cwd=root, capture_output=True, text=True, env=environment)


def test_rebuild_is_model_free_and_derives_claims_from_the_bundle(bundle):
    root, _, _ = bundle
    completed = make_reports(root)
    assert completed.returncode == 0, completed.stderr
    assert "provider modules loaded: []" in completed.stdout
    assert not (root / "runs").exists()
    report = (root / "staged" / "evaluation_report.md").read_text()
    assert "2 of the 4 samples with a grounded account link have an exactly matching plan" in report
    assert "30/32 exact" in report and "1/2 requests fully pass" in report and "7 passed" in report
    assert "same code revision" in report and "Not measured in this bundle (no discovery report" in report
    usage = (root / "staged" / "usage_report.md").read_text()
    assert "1234" in usage and "estimated and unverified" in usage


def test_staging_leaves_selected_reports_untouched(bundle):
    root, _, _ = bundle
    selected = root / "code" / "evaluation" / "evaluation_report.md"
    selected.write_text("selected report\n")
    assert make_reports(root).returncode == 0
    assert selected.read_text() == "selected report\n" and (root / "staged" / "evaluation_report.md").is_file()


def corrupt_missing_predictions(inputs_dir, inputs):
    (inputs_dir / "sample_default.csv").unlink()


def corrupt_missing_diagnostics(inputs_dir, inputs):
    (inputs_dir / "sample_default.diagnostics.jsonl").unlink()


def corrupt_wrong_hash(inputs_dir, inputs):
    with (inputs_dir / "sample_default.csv").open("a") as handle:
        handle.write("\n")


def corrupt_wrong_coverage(inputs_dir, inputs):
    path = inputs_dir / "sample_default.csv"
    path.write_text("".join(path.read_text().splitlines(keepends=True)[:-1]))
    inputs["sample_runs"]["default"]["predictions_sha256"] = sha256_of(path)
    write_inputs(inputs_dir, inputs)


def corrupt_declared_configuration(inputs_dir, inputs):
    inputs["sample_runs"]["default"]["pipeline_args"] = ["--offline"]
    write_inputs(inputs_dir, inputs)


def corrupt_declared_revision(inputs_dir, inputs):
    inputs["code_revision"] = "0" * 40
    write_inputs(inputs_dir, inputs)


def corrupt_missing_custom_results(inputs_dir, inputs):
    (inputs_dir / "custom_results.json").unlink()


@pytest.mark.parametrize("corrupt,message", [
    (corrupt_missing_predictions, "default predictions is missing"),
    (corrupt_missing_diagnostics, "default diagnostics is missing"),
    (corrupt_wrong_hash, "does not match its recorded sha256"),
    (corrupt_wrong_coverage, "do not cover exactly the 32 sample case ids"),
    (corrupt_declared_configuration, "declares ['--offline']"),
    (corrupt_declared_revision, "pass --allow-revision-mismatch"),
    (corrupt_missing_custom_results, "custom results is missing"),
])
def test_missing_or_mismatched_inputs_fail_explicitly(bundle, corrupt, message):
    root, inputs_dir, inputs = bundle
    corrupt(inputs_dir, inputs)
    completed = make_reports(root)
    assert completed.returncode == 1 and message in completed.stderr
    assert not (root / "staged").exists()                                  # nothing misleading is rendered


def test_acknowledged_revision_mismatch_is_labelled(bundle):
    root, inputs_dir, inputs = bundle
    corrupt_declared_revision(inputs_dir, inputs)
    completed = make_reports(root, "--allow-revision-mismatch")
    assert completed.returncode == 0, completed.stderr
    assert "NOT a unified release" in (root / "staged" / "evaluation_report.md").read_text()


def test_altered_selected_output_fails(bundle):
    root, _, _ = bundle
    with (root / "output.csv").open("a") as handle:
        handle.write("\n")
    completed = make_reports(root)
    assert completed.returncode == 1 and "fixture_run output" in completed.stderr
    assert "does not match its recorded sha256" in completed.stderr


# --- spec 0024: every final artifact is hash-verified before it is parsed or rendered --------------------------

def alter_diagnostics_flags(root):
    """Parseable, same case ids, different flags."""
    path = root / FINAL_RUN / "diagnostics.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    rows[0]["flags"] = []
    write_jsonl(path, rows)


def alter_ledger_tokens(root):
    path = root / FINAL_RUN / "usage_ledger.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    rows[0]["input_tokens"] += 123456
    write_jsonl(path, rows)


def convert_ledger_to_crlf(root):
    path = root / FINAL_RUN / "usage_ledger.jsonl"
    path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))


def drop_declared_hash(role):
    def drop(root):
        manifest = read_final_manifest(root)
        del manifest[f"{role}_sha256"]
        write_final_manifest(root, manifest)
    return drop


def malform_declared_hash(root):
    manifest = read_final_manifest(root)
    manifest["usage_ledger_sha256"] = manifest["usage_ledger_sha256"].upper()
    write_final_manifest(root, manifest)


@pytest.mark.parametrize("alter,message", [
    (alter_diagnostics_flags, "fixture_run diagnostics"),
    (alter_ledger_tokens, "fixture_run usage_ledger"),
    (convert_ledger_to_crlf, "fixture_run usage_ledger"),
    (drop_declared_hash("diagnostics"), "fixture_run diagnostics has no valid recorded sha256 (got None)"),
    (drop_declared_hash("usage_ledger"), "fixture_run usage_ledger has no valid recorded sha256 (got None)"),
    (drop_declared_hash("output"), "fixture_run output has no valid recorded sha256 (got None)"),
    (malform_declared_hash, "fixture_run usage_ledger has no valid recorded sha256"),
])
def test_final_artifact_without_a_matching_declared_hash_fails_and_leaves_reports_unchanged(bundle, alter, message):
    root, _, _ = bundle
    staged = root / "staged"
    staged.mkdir()
    for name in ("evaluation_report.md", "usage_report.md"):
        (staged / name).write_text(f"previous {name}\n")
    alter(root)
    completed = make_reports(root)
    assert completed.returncode == 1 and message in completed.stderr, completed.stderr
    assert all((staged / name).read_text() == f"previous {name}\n"
               for name in ("evaluation_report.md", "usage_report.md"))


def test_refreshed_ledger_with_its_refreshed_hash_is_accepted_and_reported(bundle):
    root, _, _ = bundle
    alter_ledger_tokens(root)
    manifest = read_final_manifest(root)
    manifest["usage_ledger_sha256"] = sha256_of(root / FINAL_RUN / "usage_ledger.jsonl")
    write_final_manifest(root, manifest)
    completed = make_reports(root)
    assert completed.returncode == 0, completed.stderr
    assert str(1234 + 123456) in (root / "staged" / "usage_report.md").read_text()
