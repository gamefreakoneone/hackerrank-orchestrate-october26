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
| 0013 | Completed | pending `spec 0013: multilingual intent gate` | 508 deletion / 10 non-deletion; 32/32 samples deletion |
| 0014–0016 | Not started | — | |

## Metrics (32 samples — an inspected regression set, not a holdout)

| Checkpoint | Status acc | Account linkage | Step F1 | Seq exact |
|---|---|---|---|---|
| 0001 stub | not measured (scorer arrives in 0005) | not measured | not measured | not measured |
| 0005 baseline (format-only stub), all 32 | 0.000 | not measured (no diagnostics) | 0.000 | 0.000 |
| 0010 discovery report, all 32 (pipeline not wired) | n/a | 12/32 grounded, precision 12/12, ungrounded 20 | n/a | n/a |
| 0012 pipeline, dev 20 | 0.750 (15/20) | 7/20 correct, 0 wrong, 13 ungrounded | 0.904 | 0.250 |
| 0012 pipeline, all 32 | 0.719 (23/32) = conditional bound | 12/32, 0 wrong | 0.898 | 0.281 |

## Output stage

**format-only baseline** at root — root `output.csv` holds 518 `NOT_APPLICABLE,[]` rows from the spec 0001 stub (untracked,
not committed). No audited output has been promoted. A development full pass of the audited pipeline with the intent gate exists at
`runs/all.csv` (validator clean; 461 INCOMPLETE / 47 COMPLETE / 10 NOT_APPLICABLE) — a development run, not the
cold-cache final run required by spec 0015.

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

- Continue with spec 0014.
- Pricing for the three models is not established (`code/config/pricing.yaml` empty); usage report must source prices or say cost is unavailable.

## Submission checklist / trace

See `code/docs/SUBMISSION_CHECKLIST.md`. Trace: `agent-trace/claude-code/<session>.jsonl`, refreshed before each commit.
Last published checkpoint: `14df3a9` (spec 0012).
