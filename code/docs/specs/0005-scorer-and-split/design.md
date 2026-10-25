# Spec 0005 — scorer-and-split: design

Contracts: `code/docs/TECHNICAL_DESIGN.md` §3. Data facts: §5.

- Matching: multiset match of step keys; field accuracy computed only over matched pairs.
- Sequence exact: predicted `steps_json` equals gold after JSON parse (key order ignored).
- LCS over the ordered list of step keys / max(len).
- Split: sort sample case_ids, `random.Random(20261025)` shuffle within each status, take 2/3 per stratum (dev).
- Reads `sample_output.csv` (allowed here; evaluation only).
