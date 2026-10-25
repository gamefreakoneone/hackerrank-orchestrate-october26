"""Custom and metamorphic validation cases (not a holdout): python code/evaluation/run_custom.py [--offline] [NAME ...]

Each code/evaluation/cases/<name>/ holds request.csv, overlay/ (files appended to or added beside a temporary copy
of dataset/), expected.csv and expected_flags.json. dataset/ itself is never modified.
"""
from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from pathlib import Path

EVALUATION_DIR = Path(__file__).resolve().parent
REPO_ROOT = EVALUATION_DIR.parents[1]
CASES_DIR = EVALUATION_DIR / "cases"
sys.path.insert(0, str(REPO_ROOT / "code"))

import main as pipeline_main  # noqa: E402


def build_overlay_dataset(case_dir: Path, target: Path) -> Path:
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(REPO_ROOT / "dataset", target)
    shutil.copyfile(case_dir / "request.csv", target / "deletion_requests.csv")
    overlay = case_dir / "overlay"
    for source in sorted(p for p in overlay.rglob("*") if p.is_file()):
        destination = target / source.relative_to(overlay)
        if source.suffix == ".csv" and destination.exists():
            with source.open(encoding="utf-8", newline="") as handle:
                rows = list(csv.reader(handle))[1:]
            with destination.open("a", encoding="utf-8", newline="") as handle:
                csv.writer(handle, lineterminator="\n").writerows(rows)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
    return target


def read_output(path: Path) -> dict[str, tuple[str, list]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return {r["case_id"]: (r["deletion_status"], json.loads(r["steps_json"])) for r in csv.DictReader(handle)}


def run_case_dir(case_dir: Path, offline: bool) -> list[dict]:
    work = REPO_ROOT / "runs" / "custom"
    dataset_copy = build_overlay_dataset(case_dir, work / f"tmp_{case_dir.name}")
    output = work / f"{case_dir.name}.csv"
    exit_code = pipeline_main.main(["--cases", "all", "--data-root", str(dataset_copy), "--out", str(output),
                                    *(["--offline"] if offline else [])])
    expected = read_output(case_dir / "expected.csv")
    actual = read_output(output)
    diagnostics = {d["case_id"]: d for d in map(json.loads, output.with_suffix(".diagnostics.jsonl").read_text().splitlines())}
    flag_rules = json.loads((case_dir / "expected_flags.json").read_text())
    results = []
    for case_id, (status, steps) in sorted(expected.items()):
        got_status, got_steps = actual[case_id]
        flags = set(diagnostics[case_id]["flags"])
        rule = flag_rules.get(case_id, {"present": [], "absent": []})
        flags_ok = set(rule["present"]) <= flags and not (set(rule["absent"]) & flags)
        results.append({"case": case_dir.name, "case_id": case_id, "validator_ok": exit_code == 0,
                        "status_ok": got_status == status, "steps_ok": got_steps == steps, "flags_ok": flags_ok,
                        "expected_status": status, "got_status": got_status, "flags": sorted(flags)})
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("names", nargs="*")
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args(argv)
    case_dirs = [d for d in sorted(CASES_DIR.iterdir()) if d.is_dir() and (not args.names or d.name in args.names)]
    results = [r for d in case_dirs for r in run_case_dir(d, args.offline)]
    lines = ["| case | request | expected | got | status | steps | flags | validator | flags seen |",
             "|---|---|---|---|---|---|---|---|---|"]
    for r in results:
        mark = lambda ok: "pass" if ok else "FAIL"
        lines.append(f"| {r['case']} | {r['case_id']} | {r['expected_status']} | {r['got_status']} | {mark(r['status_ok'])} | "
                     f"{mark(r['steps_ok'])} | {mark(r['flags_ok'])} | {mark(r['validator_ok'])} | {' '.join(r['flags'])} |")
    passed = sum(all((r["status_ok"], r["steps_ok"], r["flags_ok"], r["validator_ok"])) for r in results)
    lines.append(f"\n{passed}/{len(results)} requests fully pass")
    report = "\n".join(lines)
    print(report)
    (REPO_ROOT / "runs" / "custom").mkdir(parents=True, exist_ok=True)
    (REPO_ROOT / "runs" / "custom" / "results.md").write_text(report + "\n", encoding="utf-8")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
