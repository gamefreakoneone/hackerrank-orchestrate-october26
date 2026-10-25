# Corrective-pass review — targeted findings and implementation handoff

- **Audited SHA:** `88a357ea152601aeca3ce5cc98e0fd764597b1c6`
- **Branch:** `claude/specs-0017-0021-5s3kpe`
- **Reviewer:** OpenCode, `azure/gpt-6-astra`; **date:** 2026-10-25.
- **Execution:** read-only Plan-mode investigation through pinned Git blobs and in-memory Python `-B` execution.
  No live provider calls; local LLM/evidence caches absent. The working checkout was then at bf79d4a; source imports
  for the experiments came from 88a357e. The subsequent documentation turn switched to the target branch and ran
  `git pull --rebase origin claude/specs-0017-0021-5s3kpe`, confirming HEAD at the audited SHA before documentation edits.
  Both Python component reproductions printed below were then rerun successfully on that synced runtime during
  documentation validation; neither invokes the pipeline or writes selected artifacts.
- **Scope:** four confirmed defects: **1 blocker, 3 major**. Minor findings are not finalized. This is a targeted
  review, not completion of the original exhaustive audit. The user next requested executable specs and a handoff;
  unresolved audit questions are listed below rather than represented as completed work.

## Reproduction table

| Requested check / claim | Independently observed | Method / limitation |
|---|---|---|
| pytest: 163 passed, 2 skipped | **not measured** | No pytest suite run in the read-only audit |
| output SHA matches manifest: 81b31784…0ecb | matches | SHA-256 of pinned Git blob bytes |
| diagnostics and usage-ledger hashes match | both match | SHA-256 of pinned Git blob bytes |
| validator: 0 errors / 105 warnings | 0 / 105 | Actual target validate_output function with memory-backed target files, not CLI |
| rebuilt reports byte-identical | both identical | Actual target loaders/renderers in memory: evaluation 9,218 bytes; usage 2,560 bytes; CLI not run |
| sample: 23/32, F1 0.896, exact 9/32, linkage 12/32 | 23/32; F1 0.895774647887324; 9/32; 12/32 | Actual target score function on preserved sample blobs, not new inference |
| package contents/exclusions | 271 entries; required files present; configured secret scan 0 findings | In-memory ZIP using target tracked paths and packaging filters; 447,849 bytes; actual make_zip CLI/extraction not run |
| independent output contract check | 518 unique matching case IDs; 2,693 steps; no mechanical errors | Standard-library script independent of repo validator; checks listed below |

All hashes:

```text
output.csv: 81b317844674c62981d43b3c6eb575fc30520737d5e32078de3ea9a86e9e0ecb
diagnostics.jsonl: ae42396fadf29f402a996e051cd6d26cab5a805f8368e0fe2a27ac72888ef56e
usage_ledger.jsonl: 445a8b5b1024577a528e4a8f912add4f305491a41429539b95d419f183a293b3
```

The independent check covered exact columns/step keys, integer consecutive step_no, operation/state/phase pairs,
canonical step order, duplicates, NOT_APPLICABLE iff empty, COMPLETE verification-only with evidence, INCOMPLETE
future evidence empty, and all 862 citations existing and captured by audit_at. All citations were file IDs.
Rows are numerically sorted by case suffix, consistent with existing serialization; they are not lexicographically
sorted. This is recorded as an interpretation detail, not counted as a new defect.

Distribution: 49 COMPLETE / 459 INCOMPLETE / 10 NOT_APPLICABLE. Steps: 721 FINDING / 721 REMEDIATION /
1,251 VERIFICATION. There are 105 INCOMPLETE rows without findings/remediation; diagnostic blockers make these
validator warnings. Mechanical validation does not establish their semantic completeness or hidden-answer accuracy.

## Confirmed findings

### B1 — Future observations are backdated into at-cutoff account state

**Severity:** blocker. **References at 88a357e:** `code/ghostaudit/evidence/index.py:49–50`,
`code/ghostaudit/timeline.py:105–108,126–138`, `code/ghostaudit/evidence/json_.py:31–35`.

| Affected output row / resource | Evidence | NOT_FOUND recorded_at = audit_at | FOUND recorded_at |
|---|---|---|---|
| case_135 / account_1417 | evidence_13 | 2026-08-12T09:00:00Z | 2026-08-14T09:00:00Z |
| case_383 / account_5043 | evidence_36 | 2026-04-09T12:00:00Z | 2026-04-11T12:00:00Z |

Both files' manifest captured_at equals the earlier time. Both records link to the subject. Eligibility admits the
whole file, and min(observed_at, captured_at) collapses the future FOUND onto the earlier NOT_FOUND time. Presence
wins the tie. The saved account obligation is PRESENT, with a finding and deletion remediation; both cases are
INCOMPLETE. The citation itself passes the file-level cutoff check.

Minimal reproduction on the audited checkout (PowerShell: pipe the block into `python -B -`; on other shells use an
equivalent stdin invocation):

```python
import sys
from pathlib import Path
sys.path.insert(0, "code")
from ghostaudit.loaders import load_dataset
from ghostaudit.evidence.index import parse_file
from ghostaudit.timeline import latest_fact_by_physical_copy, observed_presence
d = load_dataset(Path("dataset"))
for cid, fid, rid in [("case_135", "evidence_13", "account_1417"),
                      ("case_383", "evidence_36", "account_5043")]:
    request = next(r for r in d.requests if r.case_id == cid)
    observations, _ = parse_file(fid, d.evidence[fid].captured_at, d.evidence_path(fid))
    relevant = [o for o in observations if o.resource_id == rid]
    earlier = [o for o in relevant if not o.observed_at or o.observed_at <= request.audit_at]
    before = latest_fact_by_physical_copy(relevant, observed_presence, "present")["primary"]
    after = latest_fact_by_physical_copy(earlier, observed_presence, "present")["primary"]
    print(cid, before.value, after.value)
```

Observed: `case_135 present absent`, `case_383 present absent`. The executed larger counterfactual additionally
rebuilt each account obligation and substituted it into the saved obligations: planner status became COMPLETE in
both cases, with existing flags only CONDITION_DEFAULTED. **This is not a corrected full pipeline run.**

**Fix / new spec:** 0022. Enforce availability and meaningful observation-time cutoffs throughout influence paths;
retain future business dates as metadata. Do not solve this with case-specific overrides or filter-induced omission.

### M1 — Present copies without flow/restore treatment facts are dropped

**Severity:** major. **References:** `code/ghostaudit/obligations.py:48–59,95–107`.
**Affected saved rows:** not established. A non-PDF/non-PNG scan found zero analogous saved flow/backup obligations;
that is not a full live-configuration replay.

Reproduction using fictional records and the real state→obligation→planner functions:

```python
import sys
from datetime import datetime, timezone
sys.path.insert(0, "code")
from ghostaudit.evidence.derive import make_observation
from ghostaudit.evidence.index import Ledger
from ghostaudit.identity import Subject
from ghostaudit.timeline import state_at
from ghostaudit.obligations import build_obligation
from ghostaudit.planner import plan
at = datetime(2026, 9, 1, tzinfo=timezone.utc)
empty = frozenset()
subject = Subject("audit-test@example.invalid", "user_99999", empty, empty, empty, empty, empty)
for rid, system, category, required, field, preserve in [
    ("data_flow_99999", "integration_service", "DATA_FLOW", "DISABLED", "enabled", False),
    ("backup_99999", "backup_service", "BACKUP_ARCHIVE", "BLOCKED", "restore_allowed", True),
]:
    observations = []
    for copy, fid, treatment in [("primary", "evidence_99998", {field: "false"}),
                                  ("failover_replica", "evidence_99999", {})]:
        observations.append(make_observation(
            evidence_id=fid, captured_at=at, observed_at=at, source_kind="sql", container="fixture",
            physical_copy=copy, resource_id=rid, system_id=system,
            fields={"record_type": category, "user_id": subject.user_id, **treatment}))
    ledger = Ledger()
    ledger.add(observations, [])
    ledger.build_indexes()
    state = state_at(rid, system, category, at, ledger, None, subject.user_id)
    obligation = build_obligation(system_id=system, resource_id=rid, category=category, required=required,
                                 condition="TRUE", state=state, subject=subject, preservation_required=preserve)
    print(category, sorted(state.presence_by_physical_copy),
          [c.physical_copy for c in obligation.copy_states], obligation.satisfied, plan([obligation], [])[0])
```

Observed in both cases: presence copies `['failover_replica', 'primary']`, treatment copies `['primary']`,
satisfied `True`, planner `COMPLETE`. These are isolated component counterexamples, not claimed full request runs.

**Fix / new spec:** 0023. Retain UNKNOWN treatment for every relevant copy; keep supported ACTIVE findings separate
from unresolved treatment and enforce preservation independently.

### M2 — Report loader does not verify final diagnostics or usage hashes

**Severity:** major. **References:** `code/evaluation/make_reports.py:74–89`.
**Affected output rows:** none in the current output; all pinned artifact hashes actually match.

Reproduction executed in memory using the exact load_final_run function and memory-backed Path objects:

1. Load pinned output, manifest, diagnostics and ledger bytes into a mapping.
2. Change the first diagnostics record's flags to `[]`, preserving JSON validity and every case ID.
3. Call load_final_run without updating diagnostics_sha256: it returns successfully.
4. Restore diagnostics; increase the first ledger record's input_tokens by 123456 without updating its hash.
5. Call load_final_run again: it returns successfully.

Actual output:

```text
diagnostics hash_matches_manifest False load_final_run ACCEPTED
usage_ledger hash_matches_manifest False load_final_run ACCEPTED
```

The complete executed Python/AST/MemoryPath reproduction is retained in the actual OpenCode session trace. To repeat
through the real CLI, use an isolated repository fixture with copies of these files, make the same mutations there,
and run `python code/evaluation/make_reports.py --repository-root <fixture> --final-manifest <fixture-manifest>
--report-output-directory <scratch>`. Never corrupt the selected files. This CLI variant was not run by the reviewer.

**Fix / new spec:** 0024. Require/verify the declared raw-byte hashes before parsing/rendering, including missing-hash
failures; update the existing fictional fixtures rather than weakening checks.

### M3 — Sample/ablation modes can target the selected root output

**Severity:** major. **References:** `code/main.py:55–56,60,81–87`.
**Affected output rows:** none in the current output; no destructive overwrite experiment was performed.

The reviewer executed the actual CLI argument parser and the selected-output guard only, extracted with Python AST.
Results with default --out:

```text
--cases sample --offline                         SELECTED-OUTPUT GUARD ALLOWS output.csv
--ablate trust-claims --offline                   SELECTED-OUTPUT GUARD ALLOWS output.csv
--ungrounded-account-steps ranked --offline       SELECTED-OUTPUT GUARD ALLOWS output.csv
--case case_01 --offline                          REFUSED
```

The downstream code loads the sample dataset for --cases sample, validates against that set, then replaces args.out.
The finalizer's offline/ablation checks do not protect this direct main.py path. Reproduce full publication only in
an isolated selected-output fixture; never run these commands against the real selected file to demonstrate damage.

**Fix / new spec:** 0025. Validate selected-path configuration before inference or writes; preserve alternate-destination
sample/custom/offline/ablation workflows and add explicit finalizer sample-mode refusal.

## Verified-correct observations within scope

- All three pinned release artifact hashes match. Both reports rebuild byte-identically through target functions.
- `git diff --name-only b90914b 88a357e --` with PRODUCING_CODE_PATHSPECS returns no differences. Manifest, evaluation
  inputs and both reports identify `b90914b524111fb284f8a8a8bcf3c5b7ecb5835a` as producing code.
- Preserved sample results reproduce: 159 matched / 162 predicted / 193 gold steps; precision 0.981481,
  recall 0.823834, F1 0.895775. All nine status misses have ungrounded accounts. This verifies scoring, not a ceiling.
- Ledger sums: 535 noncached calls; 273,276 input / 92,347 output tokens. Per provider: Gemini 11 calls,
  18,099 input / 57,580 output; Jev 521, 254,084 / 34,709; Azure 3, 1,093 / 58. Billing/prices not independently verified.
- case_86/account_8473 has an eligible later NOT_FOUND in evidence_08 after FOUND; case_390/account_7618 has the same
  progression in evidence_36. Target parsing/state reconstruction selects the later absence for each.
- case_34/audit_record_3753 is saved as ABSENT / required PRESENT / preservation false with REQUIRED_RECORD_MISSING,
  not false COMPLETE. The non-image state path reproduced its evidence_05 omission; full bundle scope correctness
  has not been independently established.
- The real packaging test source invokes an offline sample CLI and checks its exit code/row count; the CRLF test
  includes with/without-attributes controls. Neither test was run here, so their success is not independently verified.
- All 45 pre-existing log entries had populated single harness/model context fields in the structural check, and
  the bf79d4a log bytes were a prefix of the target log. This does not verify every prior model identity or prompt.

## Outstanding audit questions and limits

- Complete the actual pytest/CLI/clean-room reproductions on a synced checkout with RUN_LIVE unset. The captured
  bundle records 159 passed / 2 skipped while excluding packaging tests; the later 163-passed claim was not rerun.
- Inspect all COMPLETE proofs semantically, copy scope/format aliases, bundle covered_subjects and observation-time
  metadata. File-ID existence and capture eligibility alone did not catch B1.
- Independently review every discovery miss against raw source, not just parsed fields. discovery_report.py:35
  searches parsed field values and excludes names; it is not a complete raw-log search. No additional grounded link
  or score improvement was established here. Reaching 85% requires 95/111 hits, 18 more than the recorded 77.
- HISTORICAL_IMPROVEMENTS remains hardcoded narrative, with historical labels/citations. Verify each number and
  causal explanation against preserved artifacts before claiming all report prose is reproducible.
- Finish finalizer interruption/provenance testing. Reading Git revision at manifest-write time and sequential
  renames remain known risks; do not describe publication as atomic. Fixture-mutated provenance is not a live-run proof.
- Finish the complete log/trace secret, verbatim-prompt and historical append-only review. Plan-mode logging for this
  session was deferred; the documentation turn appends explicitly delayed entries, not backdated history.
- No hidden-answer accuracy, fresh full inference, live cache recreation or comprehensive raw PNG/PDF audit was run.

## Submission assessment

| Artifact | Assessment | Reason |
|---|---|---|
| output.csv | **NO-GO** | Confirmed future-state contamination in two saved rows despite mechanical validation |
| code.zip | **NO-GO as an approved release** | Confirmed runtime/publication defects; actual clean-room execution pending |
| reports | Reproducible historical measurements; **not a fresh-release sign-off** | Saved numbers reproduce, but loader integrity and remaining narrative audit need work |
| log.txt / trace | **Not fully signed off** | Structural checks passed; complete hygiene/provenance review pending; delayed current-session logging disclosed |

Implement specs 0022–0025 using `../CORRECTIVE_HANDOFF_0022_0025.md`. Preserve the saved release until authorized
regeneration; code fixes alone do not change the provenance or correctness of previously produced output.
