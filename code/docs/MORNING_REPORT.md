# MORNING_REPORT — overnight run

Run: unattended, Claude Code session `ec35ed67-5cb9-5bde-94dc-96a460a90186` (cloud session
`session_01W4Ze6mbVNu5rNRyb4mLfBz`), model `claude-opus-5-5`, 2026-10-25 07:51Z → ~09:30Z.
Branch: the session's designated push branch `claude/nifty-tesla-4ig5f5`, fast-forwarded to
`origin/claude/eager-cray-7fhtkf` @ `5b977de` before any edit; every checkpoint is pushed there
(`claude/eager-cray-7fhtkf` itself was not written). Merge or fast-forward it into eager-cray if that branch is the target.

No time, call or spend limit was configured; none was assumed. No deadline is configured in the repository.
Official challenge / submission page:
https://www.hackerrank.com/contests/hackerrank-orchestrate-october26/challenges/ghost-data-still-exists
Nothing was submitted.

## Bottom line

- **All specs 0001–0016 are Completed.** Spec 0010 is Completed with its sample resource-recall target not met (77/111
  vs ≥ 85%): the gap comes from the grounding contract, not missing code (details below).
- **Root `output.csv` is the selected audited output**: cold-cache final run `output_candidate_20261025T085130Z`, code
  `375604e`, sha256 `09c8ecf6781e295799866b3e875c21f456de240f8d0b31f4b960a8f59ac786e3`, 518 rows, validator 0 errors
  (104 warnings, each an INCOMPLETE case with a blocker flag). INCOMPLETE 461, COMPLETE 47, NOT_APPLICABLE 10.
- **Output stage: submission artifacts validated together.** output.csv ↔ manifest ↔ diagnostics ↔ usage ledger ↔
  reports ↔ code.zip were checked against each other (make_reports verifies the checksum; code.zip built from the same
  tree, clean-room run passes). This is file and consistency validity, **not** hidden-answer accuracy.
- Samples (an inspected regression set): status 23/32, account linkage 12/32 with 0 wrong, step F1 0.898, sequence
  exact 9/32. The 9 status misses are all gold-COMPLETE samples without a grounded account link.

## Spec ledger

| Spec | Status | Commit(s) | Notes |
|---|---|---|---|
| 0001 | Completed | `15c97a8` | live smoke: jev, azure, gemini OK |
| 0002 | Completed (before this run) | `66e8559` and earlier | recon |
| 0003 | Completed | `0695b52` | typed models + loaders |
| 0004 | Completed | `84bbd03` | serializer + hard validator; sample_output.csv validates clean |
| 0005 | Completed | `4f192d3` | scorer, frozen 20/12 split, baseline |
| 0006 | Completed | `b22c8d9` | 518/518 resolved, 100 via historical email |
| 0007 | Completed | `2cb0e29` | 3012 observations, 472 coverage rows |
| 0008 | Completed | `c188935` | shared LLM layer; live tests pass |
| 0009 | Completed | `04c26e4` | 23 PNG records; the 8 "unreachable" resources are not in any PNG |
| 0010 | Completed — recall target not met (contract-bound) | `f63f611` | linkage 12/32, precision 12/12; 166/508 deletion requests grounded |
| 0011 | Completed | `ef07015` | 77/77 discovered gold obligations correct |
| 0012 | Completed | `14df3a9` | end-to-end; dev status 0.750, F1 0.904 |
| 0013 | Completed | `0623153` | intent: 508 deletion / 10 non-deletion; 32/32 samples deletion |
| 0014 | Completed | `d33daa7` (expected outputs before running), `06ce215` | 9/9 custom requests; 4 metamorphic tests |
| 0015 | Completed | `375604e` (code freeze), `6d08f84` | cold final run, ablations, reports |
| 0016 | Completed | `ca11239`, `abefc0f` | code.zip, README, interview notes |
| wrap-up | — | `trace: overnight wrap-up` (this commit) | reports, trace, checklist |

## Metrics (32 samples — inspected regression set, not a holdout)

| Checkpoint | Status acc | Account linkage | Step F1 | Seq exact |
|---|---|---|---|---|
| 0005 baseline (format-only stub) | 0.000 | not measured | 0.000 | 0.000 |
| 0010 discovery (pipeline not wired) | n/a | 12/32 grounded, 0 wrong, 20 ungrounded | n/a | n/a |
| 0012 pipeline, dev 20 | 0.750 | 7/20, 0 wrong | 0.904 | 0.250 |
| final code, dev 20 / holdout 12 | 0.750 / 0.667 | 7/20 / 5/12 | 0.904 / 0.889 | 0.250 / 0.333 |
| **final code, all 32** | **0.719 (23/32)** | **12/32, 0 wrong** | **0.898 (P 0.988, R 0.824)** | **0.281 (9/32)** |

Also: reconstructed state agrees with gold for 104/111 sample resources (7 have no eligible evidence at all) and 75/75
gold citations are reproduced (`code/tools/state_report.py`). Custom validation 9/9. Ablations: no model 21/32,
no history 22/32, trust claims 23/32, ranked guessed accounts 23/32 status / 13/32 exact (guesses wrong 12/20).

## Output and usage

| Item | Value |
|---|---|
| Selected run | `output_candidate_20261025T085130Z` (`python code/main.py --cases all --no-cache --out runs/final/output_candidate.csv`) |
| Producing code | `375604e` (only report/test/doc files changed afterwards) |
| Root `output.csv` | byte-identical copy, sha256 `09c8ecf6…786e3`, validator 0 errors |
| Diagnostics / ledger / manifest | `code/evaluation/final_run/` |
| Model usage | 535 real calls (Jev 521, Gemini 11, Azure 3), 273,276 in / 88,704 out tokens; est. $0.2266 total, $0.00044 per request — **third-party price estimates** (no official price page found) |
| Reports | `code/evaluation/evaluation_report.md`, `code/evaluation/usage_report.md` |
| Determinism | the cold run reproduced the earlier cached pass on all 518 rows |

## Providers

| Provider | Live smoke | Pipeline use |
|---|---|---|
| Jev (TypeSafe; `JEV_MODEL=jev-latest` → served `jev-1.14.0`) | OK | intent gate, category fallback — live |
| Azure OpenAI via Strands (`gpt-6-luna`) | OK (needs `reasoning_effort=none` for function tools) | intent adjudication — live |
| Gemini via Strands (`gemini-3.8-flash`) | OK | PNG extraction — live |
Offline (`--offline`) is tested and works: keyword intent (marked provisional), no PNG facts, no category fallback.

## Observed failure patterns (from diagnostics and sample analysis)

1. **Ungrounded accounts dominate**: 20/32 samples and 342/508 deletion requests have no grounded subject→account
   link — only an identifier-free DELETE_RECORD claim connects the account (e.g. case_01, case_25). They carry
   ACCOUNT_UNGROUNDED and cannot be COMPLETE; 9 of the 10 gold-COMPLETE samples are in this group.
2. **Anonymized analytics without a link** (case_03, case_04, case_21, case_25–28): identifiers already nulled, reachable
   only through workflow claims → not discovered.
3. **No eligible evidence** for 7 retained audit records (case_09, 18, 20, 23, 24, 29, 30) → VERIFY_RECORD_PRESENT
   missing.
4. **Replica preference in the absence rule** (case_24): an older replica-covering snapshot suppresses a newer bundle
   omission; gold-consistent on samples, documented by the moved-file metamorphic test.

## [overnight] decisions (also in TECHNICAL_DESIGN decision log)

- Pushed to the session branch `claude/nifty-tesla-4ig5f5` instead of `claude/eager-cray-7fhtkf`.
- Azure via Strands needs `reasoning_effort=none`; base URL = endpoint + `/openai/v1/`.
- Evidence: inventory coverage only for systems in `snapshot_scope`; generic-store coverage only for collections present
  in the file; free-text names never identifiers; trace records ignore infrastructure lines.
- State: an omission must cover the replica where the record was last seen; `*_completed` reads count as presence;
  an absent record satisfies REDACTED/ANONYMIZED/DISABLED/BLOCKED but never PRESENT.
- PNG rows take the screen's category only for resources of the screen's system; vision emails outside the identity
  universe are dropped.
- No separate `cite.py`: the state proof is the citation.
- Intent: Jev accepted only when confident and consistent with the keyword cross-check; Azure adjudicates otherwise.
- Prices: third-party estimates with sources in `code/config/pricing.yaml`.

**Regressions:** none unexplained. The only metric that "fell" was spec 0010's planned recall target, which the grounding
contract makes unattainable on these samples (kept deliberately; ranked guesses are wrong 12/20 times).

## Remaining blockers and prioritized next actions

1. **Decide whether to submit this output as is.** It is valid and self-consistent; its accuracy ceiling is set by the
   grounding rule (68% of deletion requests stay INCOMPLETE for want of a grounded account). Confirm the deadline on the
   challenge page — none is configured here.
2. Rebuild `code.zip` right before upload (`python code/tools/make_zip.py`; it is gitignored) and zip the trace
   (`zip -r agent-trace.zip agent-trace`). Both were built and verified at wrap-up.
3. If time allows: look for additional *grounded* account evidence in the full dataset (not ranked guesses); the
   ranked-account ablation shows what guessing would cost (precision 0.923, 12/20 wrong on samples).
4. Prices: replace the third-party estimates with official prices if available, then rerun `make_reports.py`.

## Submission checklist / trace

`code/docs/SUBMISSION_CHECKLIST.md` — all rows ready except the human steps (upload, interview).
Trace: `agent-trace/claude-code/ec35ed67-5cb9-5bde-94dc-96a460a90186.jsonl` (redacted copy of this session),
re-exported and parsed before every commit (it cannot contain messages after its last export); earlier OpenCode
sessions in `agent-trace/opencode/`. Root `log.txt` has a SESSION START, the verbatim kickoff prompt and one
continuation entry per completed spec.
Last published checkpoint before wrap-up: `abefc0f` (spec 0016).
