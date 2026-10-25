import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evaluation"))

import score  # noqa: E402


def step(n, op, resource, phase="VERIFICATION", state="ABSENT", evidence=""):
    return {"step_no": n, "phase": phase, "system_id": "account_service", "resource_id": resource,
            "operation": op, "state": state, "evidence_id": evidence}


GOLD = {
    "case_01": ("COMPLETE", [step(1, "VERIFY_RECORD_ABSENT", "account_1", evidence="evidence_54")]),
    "case_02": ("INCOMPLETE", [step(1, "REPORT_REMAINING_RECORD", "account_2", "FINDING", "PRESENT", "evidence_9"),
                               step(2, "DELETE_RECORD", "account_2", "REMEDIATION"),
                               step(3, "VERIFY_RECORD_ABSENT", "account_2")]),
}


def test_perfect_prediction_scores_one():
    result = score.score(GOLD, GOLD, ["case_01", "case_02"], {})
    assert result["status_accuracy"] == 1.0 and result["step_f1"] == 1.0
    assert result["sequence_exact"] == 1.0 and result["mean_lcs"] == 1.0
    assert all(v == 1.0 for v in result["field_accuracy"].values())
    assert result["account_linkage"] == {"not_measured": 2}


def test_partial_prediction_metrics():
    pred = {
        "case_01": ("INCOMPLETE", [step(1, "VERIFY_RECORD_ABSENT", "account_1", evidence="")]),
        "case_02": ("INCOMPLETE", [step(1, "DELETE_RECORD", "account_2", "REMEDIATION"),
                                   step(2, "VERIFY_RECORD_ABSENT", "account_2"),
                                   step(3, "VERIFY_RECORD_ABSENT", "account_9")]),
    }
    diagnostics = {"case_01": {"case_id": "case_01", "flags": ["ACCOUNT_UNGROUNDED"],
                               "account_link": {"via": "ungrounded", "current": None}},
                   "case_02": {"case_id": "case_02", "flags": [],
                               "account_link": {"via": "grounded", "current": "account_2"}}}
    result = score.score(pred, GOLD, ["case_01", "case_02"], diagnostics)
    assert result["status_accuracy"] == 0.5
    assert result["totals"]["matched"] == 3
    assert abs(result["step_precision"] - 3 / 4) < 1e-9 and abs(result["step_recall"] - 3 / 4) < 1e-9
    assert result["field_accuracy"]["evidence_id"] == 2 / 3
    assert result["field_accuracy"]["step_no"] == 1 / 3
    assert result["sequence_exact"] == 0.0
    assert abs(result["mean_lcs"] - (1.0 + 2 / 3) / 2) < 1e-9
    assert result["account_linkage"] == {"correct": 1, "ungrounded": 1}
    assert result["flag_counts"]["ACCOUNT_UNGROUNDED"] == 1


def test_lcs_length():
    assert score.lcs_length(list("abcd"), list("acbd")) == 3
    assert score.lcs_length([], list("ab")) == 0
