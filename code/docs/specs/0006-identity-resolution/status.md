# Spec 0006 — identity-resolution: status

**Status:** Completed (2026-10-25, overnight run)

## Evidence

```text
$ python -m pytest code/tests/test_identity.py -q
9 passed
$ python code/evaluation/run_eval.py --split dev        # runs/score_20261025T080220Z_dev.md
Status accuracy 0/20; step F1 0.000 (125 gold); sequence exact 0/20   (identity not yet wired into the pipeline)
Resolution measurement: samples 32/32 resolved (3 historical request emails); all 518/518 resolved
(100 historical request emails); IDENTITY_SNAPSHOT_AFTER_CUTOFF 0/518.
```

## Scorer snapshot (dev)

| | Status acc | Account linkage | Step F1 | Seq exact |
|---|---|---|---|---|
| before (0005 stub) | 0.000 | not measured | 0.000 | 0.000 |
| after | 0.000 | not measured | 0.000 | 0.000 |

Unchanged as expected: the resolver is not used by the stub pipeline yet.

## Notes

- Email→user lookup is built per cutoff from eligible values only (snapshot if `updated_at ≤ audit_at`, audit
  email old/new with `event_time ≤ audit_at`); exact string first, then lower-case. 0 emails map to >1 user; a
  collision raises (fail fast) rather than picking one.
- Identifiers: request email, eligible snapshot email/phone/name/email_hash, pre-cutoff audit old/new values;
  `sha256(email)` added for every email. Phones normalized to digits, emails/hashes lower-case, names NFC.
- `Subject.matches(value, kind)` is exact per type; names only match with `kind="name"` (no substring).
- case_12's request email is the current one (its text mentions the old address); its historical email is still
  collected. The spec's "historical email (case_10/12/29)" test was adjusted accordingly.
