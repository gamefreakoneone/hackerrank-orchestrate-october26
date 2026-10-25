# Spec 0019 — Grounded discovery coverage: status

**Status:** Completed — investigation-only outcome (no defensible new link found; metrics unchanged)
**Implementation/investigation commit / publication:** the `spec 0019: measure and improve grounded discovery`
commit on `claude/specs-0017-0021-5s3kpe`; SHA and verified remote ref in `FEATURE_STATUS.md` and the log.

## What changed

- `tools/discovery_report.py`: classifies every missed gold resource by the participant-visible evidence available
  at `audit_at` (`miss_cause`), reports account recall, other-resource recall and extra accounts separately, and can
  write the result plus the per-miss gap table as JSON (`--out`) for report rebuilding. Evaluation-only.
- `code/docs/DISCOVERY_GAP_REVIEW.md`: gap table, searches performed and conclusions.
- `code/tests/test_grounded_discovery_regressions.py`: guards not already covered (null-profile 404 and anonymized
  records do not ground; same-file co-occurrence is not ownership; repeated requests keep independent cutoffs).
- No pipeline (prediction) code changed: every miss lacks a pre-cutoff record tying it to the subject.

## Evidence

Configuration: code `b0c7f27` (0018), cached provider responses from this pass's live run (including the Gemini
extraction of all 11 PNGs, which `discovery_report.py` reads offline).

```text
python code/tools/discovery_report.py --split all --verbose      (before and after: identical JSON)
resource_recall 77/111, account_recall 12/32, other_resource_recall 65/79, extra_resources 3 (extra_accounts 1)
linkage grounded:correct 11, multi_grounded:correct 1, ungrounded 20; precision 12/12
miss_causes: workflow_claims_only 14, eligible_records_without_ownership 12, post_cutoff_evidence_only 5,
             no_participant_evidence 3 (discovery_gap 0, parser_gap_candidate 0, linked_to_other_user 0)
python -m pytest code/tests/test_grounded_discovery_regressions.py code/tests/test_discovery.py code/tests/test_identity.py -q
17 passed
python -m pytest code/tests -q
133 passed, 2 skipped
git diff --check   (clean)
```

Full dataset (518 requests, no intent gate): 167 grounded / 351 ungrounded accounts (historical diagnostics:
166/508 deletion requests grounded, which excludes the 10 NOT_APPLICABLE rows).

## Scorer snapshot

Same cached provider responses; sample outputs before/after byte-identical.

| When / split | Code revision / configuration | Status accuracy | Account linkage / coverage | Step F1 | Sequence exact |
|---|---|---|---|---|---|
| Before / dev | `b0c7f27` (0018), cached responses | 0.750 (15/20) | 7/20 correct, 13 ungrounded | 0.900 | 0.250 (5/20) |
| Before / all samples | `b0c7f27` (0018), cached responses | 0.719 (23/32) | 12/32 correct (0 wrong); recall 77/111, 3 extras | 0.896 | 0.281 (9/32) |
| After / dev | 0019 tree, cached responses | 0.750 (15/20) | 7/20 correct, 13 ungrounded | 0.900 | 0.250 (5/20) |
| After / all samples | 0019 tree, cached responses | 0.719 (23/32) | 12/32 correct (0 wrong); recall 77/111, 3 extras | 0.896 | 0.281 (9/32) |

## Investigation and publication

- The 0010 target (≥ 85% sample resource recall) remains **unmet**: 77/111 = 69.4%.
- Unsupported candidates stay in diagnostics (`account_link.ranked_candidates`); historical grounded accounts are
  preserved (case_17).
- Details: `code/docs/DISCOVERY_GAP_REVIEW.md`. Raw outputs: `runs/corrective/0019_discovery_{before,after}.json`
  (ignored run directory; spec 0020 decides what to preserve).
