# Independent Phase 0 review

- **Reviewed commit:** `66e8559` (`phase 0: technical design, spec plan, data-derived decisions`).
- **Branch reviewed:** `claude/eager-cray-7fhtkf`.
- **Date recorded:** 2026-10-25 (UTC). The audit was performed read-only earlier in this session in plan mode; its original timestamp was not recorded.
- **Reviewer:** OpenCode; runtime model `azure/gpt-6-astra`.
- **Scope:** The handoff, technical design, relevant specs, analysis scripts, and participant-facing data. No code, specs, or design documents were changed during the audit.
- **Reference convention:** All `file:line` references below refer to the reviewed revision, not to future corrections.

## Verdict

The architecture and 16-spec structure are sound, and keeping the strict cutoff is correct. The proposed follow-up should be revised: correct the planning and measurement problems below, then review the results before starting spec 0001.

The other agent correctly recommends strict cutoffs and investigating surviving identity links. Its proposed activity search will not recover the eight missing resources, and its recommendation moves into implementation before resolving the larger design problems.

## What was verified, and how

All numerical audit results below were reproduced during the read-only audit unless explicitly marked **unverified**. Reproducing a heuristic's output does not establish that its matching rules are correct.

| Check | Result | Method |
|---|---|---|
| Phase 0 commit and scope | Commit `66e8559` is on the reviewed branch; its changes are planning documents and analysis scripts, with no feature implementation. | Read `git log -4 --oneline --stat`, the changed files, and the existing empty entry-point files. |
| Latest-file citation heuristic | 75 cited sample steps: 71 match the latest eligible text file mentioning the resource; four have no eligible text candidate mentioning it. | Ran `python -B code/tools/p0_q2_evidence_selection.py`. |
| Resource reachability | Of 111 sample resources, 89 occur in pre-cutoff text evidence, 14 only in pre-cutoff activity, and eight in neither source. | An in-memory Python check used exact resource-ID tokens from participant text evidence and CSV rows, with per-case timestamp filtering. |
| Missing resources in activity/audit CSVs | None of the eight has a matching resource-ID token in either CSV, even without a cutoff. | Searched all row fields of `system_activity.csv` and `user_audit_log.csv` in memory, including activity details. |
| Original discovery measurements | The existing script reports 77/111 identifier-found resources and 45 extra non-expansion candidates. | Ran `python -B code/tools/p0_q3c_account_link.py`, which also executes the imported discovery report. These are heuristic measurements, not validated exact-match recall/precision. |
| Account-linking cutoff effect | Correct identifier-owned accounts fall from 15 to 12; the detailed table is below. | Repeated the existing account-linking heuristic in memory with per-case file/activity/audit cutoffs, keeping its current-identity handling unchanged. |
| Repeated requests | `case_33` and `case_52` use the same email; both authorize deletion at different times. | Grouped request rows by email and inspected those two request texts and timestamps. No email value is reproduced here. |
| Snapshot representation | `evidence_51` includes an empty JSON account collection; `evidence_90` is a newer eligible account inventory than `evidence_54` for `case_04`. | Inspected snapshot metadata/collection counts and compared manifest capture times, case cutoffs, and sample citations. |

The text helper deliberately returns no PNG text (`code/tools/p0_common.py:29-39`). Therefore, eight missing resources out of 111 is a sample text/CSV coverage limitation, not a proven full-dataset accuracy ceiling. Selected screenshots were inspected visually, but the audit did not reproduce an exhaustive image-inclusive reachability ceiling.

## Finding 1 — The account-linking baseline leaks future evidence

**References:** `code/tools/p0_q3c_account_link.py:9-23`, `code/tools/p0_q3c_account_link.py:30-35`, `code/tools/p0_q3_discovery.py:71-72`, `code/docs/TECHNICAL_DESIGN.md:219-229`.

The account-linking script builds historical email mappings and account ownership from every evidence file and LINK activity, without applying each case's cutoff. Its activity candidate window also needs to be bounded by `audit_at`.

The audit repeated the same heuristic with per-case file/activity/audit cutoffs and an activity-window upper bound of `min(audit_at, reported_at + 15 minutes)`, leaving current-identity handling unchanged:

| Outcome | Original | Cutoff-filtered |
|---|---:|---:|
| Correct identifier-owned account | 15 | 12 |
| Correct unique unowned candidate | 1 | 1 |
| Ambiguous | 16 | 19 |

The lost ownership links are `case_09` / `account_3960`, `case_26` / `account_5684`, and `case_27` / `account_3866`.

The discovery script also uses substring matching in `hit()`, rather than the design's promised exact matching. The existing recall numbers therefore do not validate exact-match discovery.

**Recommended correction:** Establish a cutoff-safe, exact-match baseline before measuring improvements. Investigating surviving references is useful, but improvement should not be measured against the uncorrected 15/32 figure.

## Finding 2 — Global one-to-one request/account assignment is unjustified

**References:** `code/docs/specs/0010-discovery-and-state/requirements.md:16-21`, `code/docs/specs/0010-discovery-and-state/design.md:7-9`, `code/docs/TECHNICAL_DESIGN.md:219-225`; participant request rows `case_33` and `case_52` in `dataset/deletion_requests.csv`.

The plan assumes one account per deletion request and uniquely assigns accounts across requests. The participant data contains two deletion requests using the same email at different times. Repeated requests for a subject must be supported: unique account ownership does not imply unique request ownership.

Choosing the closest workflow activity, even through an optimal assignment algorithm, does not establish an identity link.

**Recommended correction:** Prioritize timestamped identity/reference links, support repeated requests, and preserve unresolved ambiguity. Use workflow timing to rank candidates rather than as identity proof.

## Finding 3 — Snapshot absence needs a stronger data contract

**References:** `code/docs/TECHNICAL_DESIGN.md:67-86`, `code/docs/TECHNICAL_DESIGN.md:194-205`, `code/docs/specs/0007-evidence-parsers/design.md:5-11`, `code/docs/specs/0007-evidence-parsers/requirements.md:11-17`, `code/docs/specs/0012-planner-and-evidence/requirements.md:14-15`.

Allowing absence to be proven by a genuinely complete snapshot is reasonable. The proposed representation does not fully support that exception:

- `Observation` requires a `resource_id`, and parsers primarily emit rows or resource-bearing objects. An empty table or collection has no such row, but its coverage metadata is essential evidence.
- `evidence_51`, cited for `case_31`, contains an empty JSON account collection. Coverage handling must include it, not only populated SQL rows.
- The reproduced 71/71 result does not establish the fallback rule of selecting the latest eligible full-table snapshot. For example, `case_04` cites `evidence_54` despite the newer eligible account inventory `evidence_90`.

**Recommended correction:** Represent snapshot coverage separately from individual records, including system, collection, physical copy, scope, and timestamp. Choose evidence that establishes the required state, not merely a file that mentions the resource.

## Finding 4 — Unresolved resources can incorrectly become COMPLETE

**References:** `code/docs/specs/0010-discovery-and-state/requirements.md:19-21`, `code/docs/specs/0012-planner-and-evidence/requirements.md:11-16`, `code/docs/TECHNICAL_DESIGN.md:103-128`.

Spec 0010 says an unresolved account produces no account step. Spec 0012 says a case is COMPLETE if every obligation is satisfied. Together, these rules can drop an unresolved account and declare completion using only the remaining obligations. An empty obligation list has the same problem.

**Recommended correction:** Make unresolved identity, incomplete discovery, and unknown state explicit completion blockers. Specify how these cases are reported without inventing findings or evidence.

## Finding 5 — Sample observations became overly restrictive rules

**References:** `code/docs/specs/0012-planner-and-evidence/requirements.md:14-15`, `problem_statement.md:124-127`, `AGENTS.md:308-316`, `code/docs/specs/0011-policy-obligations/requirements.md:18-20`, `code/docs/TECHNICAL_DESIGN.md:241-248`.

Two sample-derived restrictions need correction:

1. **File-only citations:** The plan prohibits activity/audit citations, while the participant specification explicitly permits them when they support the claim. The absence of these citation types in samples does not justify banning them.
2. **Default policy branches:** The plan applies defaults and only warns about contradictory retention/hold fields. Not observing exceptions does not justify ignoring explicit conditions when they occur.

**Recommended correction:** Preserve the supplied policy and evidence contract. Distinguish conditions that are supported, false, or unknown.

## Evaluation and housekeeping corrections

- **The planned holdout is already exposed.** Phase 0 examined all 32 sample answers and used them to make design decisions. The planned 12-case holdout can remain a regression split, but should not be presented as untouched validation. References: `code/docs/TECHNICAL_DESIGN.md:163-164`, `code/docs/specs/0005-scorer-and-split/requirements.md:14-15`, `code/docs/specs/0015-full-run-ablations-reports/design.md:7`.
- **Two scorer tables are missing.** Both `code/docs/specs/0005-scorer-and-split/status.md:1-10` and `code/docs/specs/0008-llm-provider-layer/status.md:1-10` lack the before/after table required by `CLAUDE.md:28-29`.
- **Provider readiness is not established.** Live provider calls were deferred by the handoff when the smoke script did not exist (`code/docs/HANDOFF.md:165-167`). MCP availability and populated environment variables do not verify provider access. The previous agent's claims about its Python 3.13 environment, installed packages, nine populated provider variables, and Strands/TypeSafe availability are **unverified by this reviewer**; they describe that agent's environment. Live provider access was not tested during this audit.
- **The citation result remains a heuristic.** The 71/71 match is reproduced, but does not establish a universal state-reconstruction rule or validate the full-table fallback.

## Recommended correction pass

Keep the architecture and 16-spec structure. Before starting spec 0001:

1. Correct cutoff-safe discovery/linking measurements, including exact matching.
2. Replace mandatory one-to-one request/account assignment with timestamped, provenance-backed linkage that supports repeated requests and ambiguity.
3. Specify empty-snapshot coverage and unknown-state handling.
4. Correct citation and policy-condition restrictions.
5. Correct evaluation claims and add the missing scorer tables to both 0005 and 0008.

Summarize the corrections and review their results before implementation. Keep the strict cutoff; do not use post-cutoff files for discovery or state decisions.
