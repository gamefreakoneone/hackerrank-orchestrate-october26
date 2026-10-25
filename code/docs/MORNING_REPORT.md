# MORNING_REPORT — overnight run

Run: unattended, Claude Code session `ec35ed67-5cb9-5bde-94dc-96a460a90186` (cloud session
`session_01W4Ze6mbVNu5rNRyb4mLfBz`), model `claude-opus-5-5`. Started 2026-10-25T07:51Z.
Branch: the session's designated push branch `claude/nifty-tesla-4ig5f5`, fast-forwarded to
`origin/claude/eager-cray-7fhtkf` @ `5b977de` before any edit; all checkpoints are pushed there
(eager-cray itself is not written by this run).

No time, call or spend limit was configured by the user or platform; none is assumed. No deadline is configured.

## Spec ledger

| Spec | Status | Commit | Notes |
|---|---|---|---|
| 0001 | Completed | `15c97a8` | live smoke: jev OK, azure OK, gemini OK |
| 0002 | Completed (before this run) | `66e8559` and earlier | recon |
| 0003 | Completed | `0695b52` | 7 tests |
| 0004 | Completed | `84bbd03` | 13 tests; validator clean on sample_output.csv |
| 0005 | Completed | `4f192d3` | baseline recorded |
| 0006 | Completed | `b22c8d9` | 518/518 resolved, 100 historical request emails |
| 0007 | Completed | `2cb0e29` | 3012 observations, 472 coverage rows |
| 0008 | Completed | `c188935` | live: jev, azure, gemini OK |
| 0009 | Completed | `04c26e4` | 23 PNG records; 8 unreachable resources not in PNGs |
| 0010 | Completed (recall target not met, contract-bound) | `f63f611` | linkage 12/32 (0 wrong); 167/518 grounded |
| 0011 | Completed | `ef07015` | 77/77 discovered gold obligations correct |
| 0012 | Completed | `14df3a9` | dev status 0.750, F1 0.904 |
| 0013 | Completed | `0623153` | 508 deletion / 10 non-deletion; 32/32 samples deletion |
| 0014 | Completed | `d33daa7` (expected outputs, before running) + `06ce215` | 9/9 custom requests pass; 4 metamorphic tests |
| 0015 | Completed | `375604e` (code freeze) + `6d08f84` | final run 535 calls, est. $0.23 |
| 0016 | Completed | `ca11239` + pending `spec 0016: packaging, README and interview notes` | code.zip verified clean-room |

## Metrics (32 samples — an inspected regression set, not a holdout)

| Checkpoint | Status acc | Account linkage | Step F1 | Seq exact |
|---|---|---|---|---|
| 0001 stub | not measured (scorer arrives in 0005) | not measured | not measured | not measured |
| 0005 baseline (format-only stub), all 32 | 0.000 | not measured (no diagnostics) | 0.000 | 0.000 |
| 0010 discovery report, all 32 (pipeline not wired) | n/a | 12/32 grounded, precision 12/12, ungrounded 20 | n/a | n/a |
| 0012 pipeline, dev 20 | 0.750 (15/20) | 7/20 correct, 0 wrong, 13 ungrounded | 0.904 | 0.250 |
| 0012 pipeline, all 32 | 0.719 (23/32) = conditional bound | 12/32, 0 wrong | 0.898 | 0.281 |
| 0015 final code, all 32 | 0.719 (23/32) | 12/32, 0 wrong | 0.898 | 0.281 (9/32) |

## Output stage

**audited pipeline checkpoint** — root `output.csv` is the cold-cache final run `output_candidate_20261025T085130Z`
(code `375604e`, sha256 `09c8ecf6781e295799866b3e875c21f456de240f8d0b31f4b960a8f59ac786e3`), validator 0 errors / 104
blocker warnings; INCOMPLETE 461, COMPLETE 47, NOT_APPLICABLE 10. Matching diagnostics, usage ledger and manifest:
`code/evaluation/final_run/`. Usage: 535 calls, 273,276 in / 88,704 out tokens, est. $0.2266 ($0.00044/request).
Not yet "submission artifacts validated together" (code.zip is spec 0016). File validity is not hidden-answer accuracy.

## Providers

| Provider | Live smoke (spec 0001) | Pipeline use |
|---|---|---|
| Jev (TypeSafe, `JEV_MODEL=jev-latest` → served `jev-1.14.0`) | OK (also via shared layer, 0008) | intent gate (0013) + category fallback (0011), live |
| Azure OpenAI via Strands (`AZURE_DEPLOYMENT_FALLBACK` = gpt-6-luna) | OK (needs `reasoning_effort=none` for function tools; temperature 0 accepted) | intent adjudication (0013), live |
| Gemini via Strands (`GEMINI_VISION_MODEL` = gemini-3.8-flash) | OK (structured output, temperature 0) | PNG extraction live (0009), 11 calls cached |

## Observed failure patterns

1. **Ungrounded accounts dominate**: 20/32 samples (351/518 overall) have no grounded subject→account link; only an
   identifier-free DELETE_RECORD claim connects the account (e.g. case_01, case_25). They carry ACCOUNT_UNGROUNDED and
   cannot be COMPLETE. 9 of the 10 gold-COMPLETE samples are in this group.
2. **Anonymized analytics without a link** (case_03, case_04, case_21, case_25–28): records whose identifiers were already
   nulled are reachable only through workflow claims, so they are not discovered.
3. **No eligible evidence** for 7 retained audit records (case_09, case_18, case_20, case_23, case_24, case_29, case_30).

## [overnight] decisions

- Pushed to `claude/nifty-tesla-4ig5f5` (session-designated branch) rather than `claude/eager-cray-7fhtkf`.
- Azure deployment rejects function tools while reasoning is on; Strands `OpenAIModel` is configured with
  `params={"reasoning_effort": "none"}`.

## Remaining blockers / next actions

- All specs done; overnight wrap-up next.
- Prices are third-party estimates (no official page found); labelled as such in the usage report.

## Submission checklist / trace

See `code/docs/SUBMISSION_CHECKLIST.md`. Trace: `agent-trace/claude-code/<session>.jsonl`, refreshed before each commit.
Last published checkpoint: `ca11239` (spec 0016 part).
