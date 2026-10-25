"""Spec 0021: a candidate replaces the selected output only after it validates; the finalizer refuses subset,
wrong-code, wrong-configuration, altered and incomplete candidates and keeps the previous bundle on failure; hashed
release artifacts keep their bytes on a CRLF checkout. Offline: no provider is called."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import main
from ghostaudit.loaders import load_dataset
from ghostaudit.provenance import sha256_of
from ghostaudit.validate import ValidationResult

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "code" / "tools"))
sys.path.insert(0, str(REPO_ROOT / "code" / "evaluation"))

import finalize_run  # noqa: E402
import make_reports  # noqa: E402

REVISION = "a" * 40
SELECTED_BYTES = b"case_id,deletion_status,steps_json\nprevious,selected,output\n"


def run_main(out: Path, *extra: str, data_root: Path | None = None) -> int:
    return main.main(["--offline", "--out", str(out), "--run-manifest-output", str(out.with_suffix(".manifest.json")),
                      *(["--cases", "all", "--data-root", str(data_root)] if data_root else ["--cases", "sample"]),
                      *extra])


def test_failed_validation_keeps_the_selected_output(tmp_path, monkeypatch):
    out = tmp_path / "output.csv"
    out.write_bytes(SELECTED_BYTES)
    monkeypatch.setattr(main, "validate_output", lambda *a, **k: ValidationResult(errors=["injected failure"]))
    assert run_main(out) == 1
    assert out.read_bytes() == SELECTED_BYTES
    manifest = json.loads(out.with_suffix(".manifest.json").read_text())
    assert manifest["published"] is False and Path(manifest["output"]).is_file()      # rejected candidate kept


def test_failed_generation_keeps_the_selected_output(tmp_path, monkeypatch):
    out = tmp_path / "output.csv"
    out.write_bytes(SELECTED_BYTES)

    def broken_case(*args, **kwargs):
        raise RuntimeError("injected generation failure")
    monkeypatch.setattr(main, "run_case", broken_case)
    with pytest.raises(RuntimeError):
        run_main(out)
    assert out.read_bytes() == SELECTED_BYTES and sorted(p.name for p in tmp_path.iterdir()) == ["output.csv"]


def test_valid_candidate_replaces_the_output(tmp_path):
    out = tmp_path / "output.csv"
    out.write_bytes(SELECTED_BYTES)
    assert run_main(out) == 0
    manifest = json.loads(out.with_suffix(".manifest.json").read_text())
    assert manifest["published"] and manifest["output_sha256"] == sha256_of(out)
    assert manifest["validation"]["errors"] == 0 and not list(tmp_path.glob("*.staged"))


@pytest.fixture
def isolated_selected_output(tmp_path, monkeypatch):
    """main.py's selected output (with diagnostics and manifest) relocated to a fixture; no inference may start."""
    selected = tmp_path / "repo" / "output.csv"
    selected.parent.mkdir()
    selected.write_bytes(SELECTED_BYTES)
    selected.with_suffix(".diagnostics.jsonl").write_text("previous diagnostics\n")
    monkeypatch.setattr(main, "SELECTED_OUTPUT", selected)

    def inference_must_not_start(*args, **kwargs):
        raise AssertionError("inference started for a refused selected-output run")
    monkeypatch.setattr(main, "load_dataset", inference_must_not_start)
    monkeypatch.setattr(main, "LLMLayer", inference_must_not_start)
    return selected


@pytest.mark.parametrize("arguments,reason", [
    (["--cases", "sample"], "--cases sample"),
    (["--case", "case_01"], "--case selector ['case_01']"),
    (["--case"], "--case selector []"),
    (["--ablate", "trust-claims"], "--ablate trust-claims"),
    (["--ablate", "no-history"], "--ablate no-history"),
    (["--ungrounded-account-steps", "ranked"], "--ungrounded-account-steps ranked"),
    (["--offline"], "--offline"),
    (["--data-root", "elsewhere/dataset"], "--data-root elsewhere/dataset"),
])
def test_non_release_run_cannot_target_the_selected_output(isolated_selected_output, monkeypatch, arguments, reason):
    selected = isolated_selected_output
    monkeypatch.chdir(selected.parent)
    for out in (str(selected), "output.csv", f"../{selected.parent.name}/output.csv"):   # resolved aliases
        with pytest.raises(SystemExit, match="refusing to replace the selected") as refusal:
            main.main(["--out", out, *arguments])
        assert reason in str(refusal.value) and "pass --out to another path" in str(refusal.value)
    assert selected.read_bytes() == SELECTED_BYTES
    assert sorted(p.name for p in selected.parent.iterdir()) == ["output.csv", "output.diagnostics.jsonl"]
    assert selected.with_suffix(".diagnostics.jsonl").read_text() == "previous diagnostics\n"


def test_release_run_publishes_to_the_selected_output(tmp_path, monkeypatch):
    """Default configuration over the canonical (fixture: sample-sized) dataset; only the provider boundary is
    replaced by the offline cache-only layer, so no model is called. The fixture manifest is test-only."""
    dataset_root = tmp_path / "dataset"
    shutil.copytree(REPO_ROOT / "dataset", dataset_root)
    shutil.copyfile(dataset_root / "sample_deletion_requests.csv", dataset_root / "deletion_requests.csv")
    selected = tmp_path / "output.csv"
    selected.write_bytes(SELECTED_BYTES)
    monkeypatch.setattr(main, "SELECTED_OUTPUT", selected)
    monkeypatch.setattr(main, "CANONICAL_DATA_ROOT", dataset_root)
    real_layer = main.LLMLayer
    monkeypatch.setattr(main, "LLMLayer", lambda **kwargs: real_layer(**{**kwargs, "offline": True}))
    assert main.main(["--out", str(selected), "--data-root", str(dataset_root), "--no-cache",
                      "--run-manifest-output", str(tmp_path / "release.manifest.json")]) == 0
    manifest = json.loads((tmp_path / "release.manifest.json").read_text())
    assert manifest["published"] and manifest["rows"] == 32 and manifest["output_sha256"] == sha256_of(selected)


@pytest.fixture
def release(tmp_path):
    """A repository whose request set is the 32 samples, an old selected bundle and a valid same-revision
    candidate plus evaluation inputs (the candidate's declared provenance is set by the fixture)."""
    root = tmp_path / "repo"
    shutil.copytree(REPO_ROOT / "dataset", root / "dataset")
    shutil.copyfile(root / "dataset" / "sample_deletion_requests.csv", root / "dataset" / "deletion_requests.csv")
    candidate_out = root / "runs" / "candidate.csv"
    assert run_main(candidate_out, data_root=root / "dataset") == 0
    candidate_manifest = candidate_out.with_suffix(".manifest.json")
    candidate = json.loads(candidate_manifest.read_text())
    usage = root / "runs" / "candidate_usage.jsonl"
    usage.write_text(json.dumps({"provider": "jev", "model": "jev-1.14.0", "task": "intent", "input_tokens": 10,
                                 "output_tokens": 0, "cached": False, "attempts": 1, "latency_ms": 1}) + "\n")
    candidate.update(git_revision=REVISION, uncommitted_producing_code=[], usage_ledger=str(usage),
                     usage_ledger_sha256=sha256_of(usage), args={**candidate["args"], "offline": False})
    candidate_manifest.write_text(json.dumps(candidate))
    bundle = root / "code" / "evaluation" / "corrective_run"
    bundle.mkdir(parents=True)
    shutil.copyfile(candidate_out, bundle / "sample_default.csv")
    shutil.copyfile(candidate_out.with_suffix(".diagnostics.jsonl"), bundle / "sample_default.diagnostics.jsonl")
    (bundle / "custom_results.json").write_text(json.dumps({"results": []}))
    inputs = {"code_revision": REVISION, "captured_at": "2026-10-25T00:00:00Z",
              "provider_configuration": {"provider_keys_present": []},
              "sample_runs": {"default": {"pipeline_args": [], "predictions": "sample_default.csv",
                                          "predictions_sha256": sha256_of(bundle / "sample_default.csv"),
                                          "diagnostics": "sample_default.diagnostics.jsonl",
                                          "diagnostics_sha256": sha256_of(bundle / "sample_default.diagnostics.jsonl")}},
              "custom_results": {"path": "custom_results.json", "sha256": sha256_of(bundle / "custom_results.json")}}
    (bundle / "evaluation_inputs.json").write_text(json.dumps(inputs))
    (root / "output.csv").write_bytes(SELECTED_BYTES)
    (root / "code" / "evaluation" / "final_run").mkdir()
    (root / "code" / "evaluation" / "final_run" / "manifest.json").write_text("{\"previous\": true}")
    (root / "code" / "evaluation" / "evaluation_report.md").write_text("previous report\n")
    return root, candidate_manifest, bundle / "evaluation_inputs.json"


def previous_bundle_is_intact(root: Path) -> bool:
    return ((root / "output.csv").read_bytes() == SELECTED_BYTES
            and (root / "code" / "evaluation" / "final_run" / "manifest.json").read_text() == "{\"previous\": true}"
            and (root / "code" / "evaluation" / "evaluation_report.md").read_text() == "previous report\n")


def finalize(root, candidate_manifest, inputs_path):
    return finalize_run.finalize(candidate_manifest, inputs_path, root, load_dataset(root / "dataset"))


def test_valid_candidate_is_published_as_one_consistent_bundle(release):
    root, candidate_manifest, inputs_path = release
    manifest = finalize(root, candidate_manifest, inputs_path)
    assert sha256_of(root / "output.csv") == manifest["output_sha256"] == sha256_of(root / "runs" / "candidate.csv")
    assert manifest["evaluation_inputs"] == "code/evaluation/corrective_run/evaluation_inputs.json"
    published = make_reports.load_final_run(root / "code" / "evaluation" / "final_run" / "manifest.json", root)
    assert published["manifest"]["git_revision"] == REVISION
    assert "same code revision" in (root / "code" / "evaluation" / "evaluation_report.md").read_text()
    assert not list(root.glob(".finalize_*")) and not list((root / "code" / "evaluation").glob("final_run.previous*"))


def as_subset(candidate, root):
    candidate["args"]["case"] = ["case_01"]


def as_empty_selector(candidate, root):
    candidate["args"]["case"] = []


def as_sample(candidate, root):
    candidate["args"]["cases"] = "sample"


def as_ranked_accounts(candidate, root):
    candidate["args"]["ungrounded_account_steps"] = "ranked"


def as_ablation(candidate, root):
    candidate["args"]["ablate"] = ["trust-claims"]


def as_offline(candidate, root):
    candidate["args"]["offline"] = True


def as_wrong_code(candidate, root):
    candidate["git_revision"] = "b" * 40


def as_uncommitted_code(candidate, root):
    candidate["uncommitted_producing_code"] = [" M code/main.py"]


def as_altered_output(candidate, root):
    with (root / "runs" / "candidate.csv").open("a") as handle:
        handle.write("\n")


def as_missing_diagnostics(candidate, root):
    (root / "runs" / "candidate.diagnostics.jsonl").unlink()


@pytest.mark.parametrize("defect,message", [
    (as_subset, r"not the release configuration: --case selector \['case_01'\]"),
    (as_empty_selector, r"--case selector \[\]"), (as_sample, "--cases sample"),
    (as_ranked_accounts, "--ungrounded-account-steps ranked"), (as_ablation, "--ablate trust-claims"),
    (as_offline, "not the release configuration: --offline"), (as_wrong_code, "capture the evaluation inputs from the same"),
    (as_uncommitted_code, "ran uncommitted producing code"), (as_altered_output, "does not match its recorded sha256"),
    (as_missing_diagnostics, "candidate diagnostics is missing"),
])
def test_defective_candidates_are_refused_and_the_previous_bundle_kept(release, defect, message):
    root, candidate_manifest, inputs_path = release
    candidate = json.loads(candidate_manifest.read_text())
    defect(candidate, root)
    candidate_manifest.write_text(json.dumps(candidate))
    with pytest.raises(SystemExit, match=message):
        finalize(root, candidate_manifest, inputs_path)
    assert previous_bundle_is_intact(root)


def test_report_staging_failure_keeps_the_previous_bundle(release, monkeypatch):
    root, candidate_manifest, inputs_path = release

    def broken_report(*args, **kwargs):
        raise RuntimeError("injected report failure")
    monkeypatch.setattr(make_reports, "evaluation_report", broken_report)
    with pytest.raises(RuntimeError):
        finalize(root, candidate_manifest, inputs_path)
    assert previous_bundle_is_intact(root)


def git(repository: Path, *arguments: str) -> None:
    """Isolated from the user's Git configuration: no global/system config files are read or written."""
    environment = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
    subprocess.run(["git", "-c", "user.name=test", "-c", "user.email=test@example.invalid", *arguments],
                   cwd=repository, env=environment, check=True, capture_output=True)


@pytest.mark.parametrize("with_attributes", [True, False])
def test_hashed_release_artifacts_keep_their_bytes_on_a_crlf_checkout(tmp_path, with_attributes):
    source, clone = tmp_path / "source", tmp_path / "clone"
    (source / "code" / "evaluation" / "final_run").mkdir(parents=True)
    artifacts = {"output.csv": b"case_id,deletion_status,steps_json\ncase_1,COMPLETE,[]\n",
                 "code/evaluation/final_run/diagnostics.jsonl": b"{\"case_id\": \"case_1\"}\n"}
    for name, data in artifacts.items():
        (source / name).write_bytes(data)
    if with_attributes:
        shutil.copyfile(REPO_ROOT / ".gitattributes", source / ".gitattributes")
    git(source, "init", "-q")
    git(source, "add", "-A")
    git(source, "commit", "-q", "-m", "fixture")
    git(tmp_path, "-c", "core.autocrlf=true", "clone", "-q", str(source), str(clone))
    unchanged = all((clone / name).read_bytes() == data for name, data in artifacts.items())
    assert unchanged is with_attributes          # without the rule the CRLF checkout changes the hashed bytes
