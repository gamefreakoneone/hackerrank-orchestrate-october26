# CLAUDE.md — Team workflow for Ghost Data Still Exists

@AGENTS.md

`AGENTS.md` (imported above) is the organizer's file. It is authoritative and must not be edited.
Its logging rules (§2, §5) apply to every session and every sub-agent: append a `SESSION START`
entry and a per-turn entry to the root `log.txt`, with exact `tool=` and `model=` values. `log.txt`
is graded (10 pts) — keep it accurate, append-only, and free of secrets.

This file adds OUR development workflow on top of AGENTS.md.

## Start of every session

0. Sync first: `git pull --rebase origin <working branch>`. Only one agent (Claude Code, Codex, …)
   works on the branch at a time; finish, commit and push before another agent starts.
1. Follow AGENTS.md §0 (read it, log `SESSION START`).
2. Read `code/docs/FEATURE_STATUS.md` to see what is done and what is next.
3. If no spec folders exist yet, read `code/docs/HANDOFF.md` and run its Phase 0.
4. Otherwise work on exactly the spec the user names (or the next `Not started` one).

## Spec-driven workflow

- Specs live in `code/docs/specs/NNNN-short-name/` with `requirements.md`, `design.md`,
  `tasks.md`, `status.md`. Work one spec at a time, in numeric order.
- Read all four files of a spec before coding. Do not start a spec whose dependencies are not `Completed`.
- When a spec's status changes, update `code/docs/FEATURE_STATUS.md`, the spec's `status.md`,
  and its `tasks.md` checkboxes in the same commit.
- Validate before committing: run the commands in the spec's `tasks.md` and paste the evidence
  (test counts, scorer numbers) into `status.md`.
- Every spec from 0005 onward must record the scorer snapshot (status accuracy, step F1,
  sequence exact-match) on the dev split in `status.md`, before and after the change.
- Commit each completed spec separately: `spec NNNN: <summary>`. Dated commits are evidence.
- Every commit includes the current `log.txt` and `agent-trace/`.
- Before the final reply of every session: run `scripts/save_trace.sh` (also wired as the Stop/SessionEnd
  hook in `.claude/settings.json`; manual run: pipe `{"session_id":…,"transcript_path":…}` to it),
  then commit and push.
- `agent-trace/` lives at the repo root, never inside `code/`, so it stays out of `code.zip`. At the end it is
  packaged separately as `agent-trace.zip` (see `agent_trace_instructions.md`).
- Keep `code/README.md` current whenever setup, commands, or env vars change.
- Preserve the Key Contracts in `code/docs/TECHNICAL_DESIGN.md` unless a spec explicitly changes them.

## Hard rules (never break)

- Use only participant-facing files under `dataset/`. No organizer files, no hardcoded labels,
  no logic keyed on specific `case_*`, `evidence_*`, `activity_*`, or resource IDs.
- `sample_output.csv` is a regression oracle only. Never read it inside the prediction pipeline.
- No evidence, activity, or audit row with a timestamp after a case's `audit_at` may influence that case.
- LLM/Jev outputs are typed facts or enum choices. They never decide the deletion status,
  generate steps, choose evidence IDs, or order steps. Code does all of that.
- Every structured LLM call goes through the shared provider layer (`code/ghostaudit/llm/`):
  schema validation, one repair retry, cache, usage ledger. No ad-hoc model calls.
- Secrets come from environment variables only. Never print, log, or commit keys. `.env` stays untracked.
- Python 3.11+, standard layout under `code/`. Pin every new dependency in `code/requirements.txt`
  in the same change.
- Code is deterministic: sorted iteration, `json.dumps(..., sort_keys=True, separators=(",", ":"))`,
  temperature 0 / fixed seeds where supported.

## Budget discipline (we are on limited credits)

- Prefer writing a small script and reading its summarized output over reading large files.
  Never dump whole evidence files, `system_activity.csv`, or full outputs into context.
- Spawn sub-agents only for genuinely parallel, independent work.
- Run the full 518-case pipeline only when a spec requires it; iterate on the 32 samples.

## Useful references

- Strands Agents docs: MCP server `strands` (see `.mcp.json`) or https://strandsagents.com
- TypeSafe Jev docs: https://docs.typesafe.ai (Python SDK: `typesafe-sdk`)
- Data facts: `code/docs/DATA_NOTES.md`, `code/docs/GOLD_TRACE.md`