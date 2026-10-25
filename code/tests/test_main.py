import csv
import json

import main


def test_sample_run_offline_writes_valid_sorted_output(tmp_path):
    output_path = tmp_path / "sample.csv"
    assert main.main(["--cases", "sample", "--offline", "--out", str(output_path)]) == 0   # validator passed
    with output_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 32
    numbers = [int(r["case_id"].split("_")[1]) for r in rows]
    assert numbers == sorted(numbers)
    assert {r["deletion_status"] for r in rows} <= {"COMPLETE", "INCOMPLETE", "NOT_APPLICABLE"}
    diagnostics = [json.loads(line) for line in output_path.with_suffix(".diagnostics.jsonl").read_text().splitlines()]
    assert [d["case_id"] for d in diagnostics] == [r["case_id"] for r in rows]
    assert all("flags" in d and "account_link" in d for d in diagnostics)
