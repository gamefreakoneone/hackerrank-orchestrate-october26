import json

from ghostaudit.models import Operation, Phase, State, Step
from ghostaudit.serialize import canonical, dumps_steps


def make_step(operation, phase, state, resource_id, evidence_id=""):
    return Step(step_no=99, phase=phase, system_id="account_service", resource_id=resource_id,
                operation=operation, state=state, evidence_id=evidence_id)


def test_canonical_sorts_by_op_order_then_ids_and_renumbers():
    steps = [
        make_step(Operation.VERIFY_RECORD_ABSENT, Phase.VERIFICATION, State.ABSENT, "account_2"),
        make_step(Operation.DELETE_RECORD, Phase.REMEDIATION, State.ABSENT, "account_1"),
        make_step(Operation.REPORT_REMAINING_RECORD, Phase.FINDING, State.PRESENT, "account_1", "evidence_01"),
        make_step(Operation.VERIFY_RECORD_ABSENT, Phase.VERIFICATION, State.ABSENT, "account_1"),
    ]
    ordered = canonical(steps)
    assert [s.step_no for s in ordered] == [1, 2, 3, 4]
    assert [(s.operation, s.resource_id) for s in ordered] == [
        (Operation.REPORT_REMAINING_RECORD, "account_1"), (Operation.DELETE_RECORD, "account_1"),
        (Operation.VERIFY_RECORD_ABSENT, "account_1"), (Operation.VERIFY_RECORD_ABSENT, "account_2")]


def test_dumps_is_compact_sorted_json():
    text = dumps_steps([make_step(Operation.VERIFY_RECORD_ABSENT, Phase.VERIFICATION, State.ABSENT, "account_1",
                                  "evidence_54")])
    assert text == ('[{"evidence_id":"evidence_54","operation":"VERIFY_RECORD_ABSENT","phase":"VERIFICATION",'
                    '"resource_id":"account_1","state":"ABSENT","step_no":1,"system_id":"account_service"}]')
    assert json.loads(text)[0]["step_no"] == 1
