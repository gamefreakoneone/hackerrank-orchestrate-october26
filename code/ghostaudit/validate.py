"""Hard validator for every output rule (AGENTS.md §6.3, §6.4, §6.6; TECHNICAL_DESIGN §3.5)."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

from ghostaudit.loaders import Dataset, load_dataset
from ghostaudit.models import BLOCKER_FLAGS, OP_ORDER, OP_PHASE, OP_STATE, Operation, Phase, Status, case_key
from ghostaudit.serialize import OUTPUT_HEADER

STEP_KEYS = {"step_no", "phase", "system_id", "resource_id", "operation", "state", "evidence_id"}
STATE_CHECK_EVENT_TYPES = {"CHECK_DATA_FLOW", "CHECK_RESTORE_ACCESS"}


@dataclass
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    activity_citations: int = 0
    audit_citations: int = 0

    @property
    def ok(self) -> bool:
        return not self.errors


def load_case_flags(diagnostics_path: Path | None) -> dict[str, set[str]]:
    if diagnostics_path is None:
        return {}
    flags_by_case: dict[str, set[str]] = {}
    for line in diagnostics_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            record = json.loads(line)
            flags_by_case[record["case_id"]] = set(record.get("flags", []))
    return flags_by_case


def _check_citation(evidence_id: str, audit_at, dataset: Dataset, activity_by_id, audit_by_id,
                    result: ValidationResult, prefix: str) -> None:
    if evidence_id in dataset.evidence:
        if dataset.evidence[evidence_id].captured_at > audit_at:
            result.errors.append(f"{prefix} cites {evidence_id} captured after audit_at")
    elif evidence_id in activity_by_id:
        activity = activity_by_id[evidence_id]
        result.activity_citations += 1
        if activity.event_type not in STATE_CHECK_EVENT_TYPES:
            result.errors.append(f"{prefix} cites operational-claim activity {evidence_id} ({activity.event_type})")
        if activity.event_time > audit_at:
            result.errors.append(f"{prefix} cites activity {evidence_id} after audit_at")
    elif evidence_id in audit_by_id:
        result.audit_citations += 1
        if audit_by_id[evidence_id].event_time > audit_at:
            result.errors.append(f"{prefix} cites audit row {evidence_id} after audit_at")
    else:
        result.errors.append(f"{prefix} cites unknown evidence id {evidence_id!r}")


def _check_steps(case_id: str, status: str, steps_json: str, audit_at, flags: set[str], dataset: Dataset,
                 activity_by_id, audit_by_id, result: ValidationResult) -> None:
    try:
        steps = json.loads(steps_json)
    except json.JSONDecodeError as error:
        result.errors.append(f"{case_id}: steps_json is not valid JSON ({error.msg})")
        return
    if not isinstance(steps, list):
        result.errors.append(f"{case_id}: steps_json is not a JSON array")
        return
    has_blocker = bool(flags & BLOCKER_FLAGS)
    if status == Status.NOT_APPLICABLE:
        if steps:
            result.errors.append(f"{case_id}: NOT_APPLICABLE must have []")
        return
    if not steps:
        message = f"{case_id}: {status} with []"
        if status == Status.INCOMPLETE and has_blocker:
            result.warnings.append(f"{message} (blocker {sorted(flags & BLOCKER_FLAGS)})")
        else:
            result.errors.append(f"{message} requires NOT_APPLICABLE or an INCOMPLETE blocker flag")
        return
    seen_keys: set[tuple] = set()
    sort_keys: list[tuple] = []
    for position, step in enumerate(steps, start=1):
        prefix = f"{case_id} step {position}"
        if not isinstance(step, dict) or set(step) != STEP_KEYS:
            result.errors.append(f"{prefix}: must be an object with exactly keys {sorted(STEP_KEYS)}")
            return
        if step["step_no"] != position or isinstance(step["step_no"], bool):
            result.errors.append(f"{prefix}: step_no {step['step_no']!r} is not consecutive from 1")
        try:
            operation = Operation(step["operation"])
        except ValueError:
            result.errors.append(f"{prefix}: unknown operation {step['operation']!r}")
            return
        if step["phase"] != OP_PHASE[operation]:
            result.errors.append(f"{prefix}: phase {step['phase']} does not match {operation}")
        if step["state"] != OP_STATE[operation]:
            result.errors.append(f"{prefix}: state {step['state']} does not match {operation}")
        if not all(isinstance(step[k], str) for k in ("system_id", "resource_id", "evidence_id")):
            result.errors.append(f"{prefix}: system_id, resource_id and evidence_id must be strings")
            return
        step_key = (operation, step["system_id"], step["resource_id"])
        if step_key in seen_keys:
            result.errors.append(f"{prefix}: duplicate (operation, system_id, resource_id) {step_key}")
        seen_keys.add(step_key)
        sort_keys.append((OP_ORDER[operation], step["system_id"], step["resource_id"]))
        phase, evidence_id = OP_PHASE[operation], step["evidence_id"]
        if status == Status.COMPLETE:
            if phase != Phase.VERIFICATION:
                result.errors.append(f"{prefix}: COMPLETE may contain only VERIFICATION steps")
            elif not evidence_id:
                result.errors.append(f"{prefix}: COMPLETE verification must cite evidence")
        elif phase == Phase.FINDING and not evidence_id:
            result.errors.append(f"{prefix}: finding must cite evidence")
        elif phase != Phase.FINDING and evidence_id:
            result.errors.append(f"{prefix}: INCOMPLETE {phase} step must have evidence_id \"\"")
        if evidence_id:
            _check_citation(evidence_id, audit_at, dataset, activity_by_id, audit_by_id, result, prefix)
    if sort_keys != sorted(sort_keys):
        result.errors.append(f"{case_id}: steps are not in canonical order (OP_ORDER, system_id, resource_id)")
    if status == Status.INCOMPLETE and not any(OP_PHASE[k[0]] == Phase.FINDING for k in seen_keys):
        message = f"{case_id}: INCOMPLETE without findings"
        if has_blocker:
            result.warnings.append(f"{message} (blocker {sorted(flags & BLOCKER_FLAGS)})")
        else:
            result.errors.append(f"{message} and no blocker flag")


def validate_output(path: Path, dataset: Dataset, diagnostics_path: Path | None = None) -> ValidationResult:
    result = ValidationResult()
    flags_by_case = load_case_flags(diagnostics_path)
    activity_by_id = {a.activity_id: a for a in dataset.activity}
    audit_by_id = {a.audit_id: a for a in dataset.audit}
    requests_by_case = {r.case_id: r for r in dataset.requests}
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader, None)
        rows = list(reader)
    if header != OUTPUT_HEADER:
        result.errors.append(f"header {header} != {OUTPUT_HEADER}")
        return result
    case_ids = [row[0] if row else "" for row in rows]
    duplicates = sorted({c for c in case_ids if case_ids.count(c) > 1})
    if duplicates:
        result.errors.append(f"duplicate case_ids: {duplicates[:10]}")
    missing = sorted(set(requests_by_case) - set(case_ids), key=case_key)
    extra = sorted(set(case_ids) - set(requests_by_case))
    if missing:
        result.errors.append(f"{len(missing)} request case_ids missing: {missing[:10]}")
    if extra:
        result.errors.append(f"{len(extra)} unknown case_ids: {extra[:10]}")
    if not extra and case_ids != sorted(case_ids, key=case_key):
        result.errors.append("rows are not sorted by case number")
    for row in rows:
        if len(row) != 3:
            result.errors.append(f"row {row[:1]} has {len(row)} columns")
            continue
        case_id, status, steps_json = row
        if case_id not in requests_by_case:
            continue
        if status not in set(Status):
            result.errors.append(f"{case_id}: invalid deletion_status {status!r}")
            continue
        _check_steps(case_id, status, steps_json, requests_by_case[case_id].audit_at,
                     flags_by_case.get(case_id, set()), dataset, activity_by_id, audit_by_id, result)
    return result


def report(result: ValidationResult) -> None:
    for message in result.errors:
        print(f"ERROR {message}")
    for message in result.warnings:
        print(f"WARNING {message}")
    print(f"validation: {len(result.errors)} errors, {len(result.warnings)} warnings, "
          f"{result.activity_citations} activity citations, {result.audit_citations} audit citations")


def cli(argv: list[str] | None = None) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="Validate an output.csv")
    parser.add_argument("path", nargs="?", type=Path, default=repo_root / "output.csv")
    parser.add_argument("--sample", action="store_true", help="validate against the 32 sample requests")
    parser.add_argument("--diagnostics", type=Path, default=None)
    parser.add_argument("--data-root", type=Path, default=repo_root / "dataset")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    result = validate_output(args.path, load_dataset(args.data_root, sample=args.sample), args.diagnostics)
    report(result)
    sys.exit(0 if result.ok else 1)
