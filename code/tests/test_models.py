from ghostaudit.models import OP_ORDER, OP_PHASE, OP_STATE, Operation, Phase, case_key


def test_operation_tables_cover_all_fifteen_operations():
    assert len(Operation) == 15
    assert set(OP_ORDER) == set(OP_PHASE) == set(OP_STATE) == set(Operation)


def test_op_order_implies_phase_order():
    phase_rank = {Phase.FINDING: 0, Phase.REMEDIATION: 1, Phase.VERIFICATION: 2}
    ordered = sorted(Operation, key=OP_ORDER.__getitem__)
    assert [phase_rank[OP_PHASE[op]] for op in ordered] == sorted(phase_rank[OP_PHASE[op]] for op in ordered)
    assert ordered[0] == Operation.REPORT_REMAINING_RECORD and ordered[-1] == Operation.VERIFY_RESTORE_BLOCKED


def test_case_key_is_numeric():
    assert sorted(["case_100", "case_9", "case_10"], key=case_key) == ["case_9", "case_10", "case_100"]
