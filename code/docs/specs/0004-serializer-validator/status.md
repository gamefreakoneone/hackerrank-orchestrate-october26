# Spec 0004 — serializer-validator: status

**Status:** Completed (2026-10-25, overnight run)

## Evidence

```text
$ python -m pytest code/tests/test_serialize.py code/tests/test_validate.py -q
13 passed
$ python code/main.py && python -c "...from ghostaudit.validate import cli;cli()"
wrote 518 rows to <repo>/output.csv (format-only baseline)
validation: 0 errors, 0 warnings, 0 activity citations, 0 audit citations   # printed by main and by cli
$ python -m pytest code/tests -q
21 passed
```

Scorer metrics: not measured (scorer arrives in spec 0005).

## Notes

- `serialize.canonical` sorts by `(OP_ORDER, system_id, resource_id)` and renumbers; `dumps_steps` uses
  `sort_keys=True, separators=(",", ":"), ensure_ascii=False`; `write_output` sorts rows by `case_key`.
- `validate.validate_output(path, dataset, diagnostics_path=None) -> ValidationResult(errors, warnings,
  activity_citations, audit_citations)` (a result object instead of a bare `list[str]` so warnings and citation counts
  travel with the errors; `ok` = no errors). Diagnostics JSONL lines are `{"case_id", "flags": [...]}`; blocker flags:
  ACCOUNT_UNGROUNDED, UNKNOWN_STATE, POLICY_UNDEFINED, EMPTY_OBLIGATIONS.
- Mutation tests (all fail as expected): swapped order, wrong state, wrong phase + bad step_no, late file citation, late
  activity citation, DELETE_RECORD activity citation, duplicate step key, INCOMPLETE `[]` without blocker flag,
  missing row + NOT_APPLICABLE with steps. Passing variants: dataset/sample_output.csv (clean), pre-cutoff
  CHECK_DATA_FLOW citation (counted), INCOMPLETE `[]` with EMPTY_OBLIGATIONS (warning).
- `main.py` validates a full run and exits 1 on errors; `--case` subsets skip validation (cannot cover every request).
