# Spec 0005 — scorer-and-split: design

Contracts: `code/docs/TECHNICAL_DESIGN.md` §3. Data facts: §5.

- Matching: multiset match of step keys; field accuracy computed only over matched pairs.
- Sequence exact: predicted `steps_json` equals gold after JSON parse (key order ignored).
- LCS over the ordered list of step keys / max(len).
- Split: sort sample case_ids, `random.Random(20261025)` shuffle within each status, take 2/3 per stratum (dev).
- Reads `sample_output.csv` (allowed here; evaluation only).
- Also report diagnostics counts per run: every flag in TECHNICAL_DESIGN §3.5 (ACCOUNT_UNGROUNDED,
  ACCOUNT_MULTI_GROUNDED, UNKNOWN_STATE, POLICY_UNDEFINED, EMPTY_OBLIGATIONS, CONDITION_DEFAULTED,
  ACTIVITY_CITATION) so their score impact is measured.
- **Account linkage accuracy** is a separate metric (gold account_service resource vs grounded link; ungrounded
  counted separately), never folded into status accuracy.
