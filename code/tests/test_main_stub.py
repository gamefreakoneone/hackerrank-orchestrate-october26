import csv
import json

import main


def test_stub_writes_one_sorted_row_per_request(tmp_path):
    output_path = tmp_path / "output.csv"
    assert main.main(["--out", str(output_path)]) == 0
    with output_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        rows = list(reader)
    assert header == ["case_id", "deletion_status", "steps_json"]
    assert len(rows) == 518
    case_numbers = [int(row[0].split("_")[1]) for row in rows]
    assert case_numbers == sorted(case_numbers)
    assert len(set(case_numbers)) == 518
    for _, status, steps_json in rows:
        assert status == "NOT_APPLICABLE"
        assert json.loads(steps_json) == []
