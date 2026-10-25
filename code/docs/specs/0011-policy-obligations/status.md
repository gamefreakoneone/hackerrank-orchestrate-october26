# Spec 0011 — policy-obligations: status

**Status:** Completed (2026-10-25, overnight run)

## Evidence

```text
$ python -m pytest code/tests/test_policy.py code/tests/test_obligations.py -q
20 passed (5 policy incl. Jev fallback with a fake provider, 15 obligation templates incl. tombstone)
$ python code/tools/obligation_report.py --split dev
gold resources with an obligation: required state correct 49/49, satisfied flag correct 49/49;
22 gold obligations missing (undiscovered: ungrounded accounts / anonymized analytics / unreachable audit records)
$ python code/tools/obligation_report.py --split all
required_ok 77, satisfied_ok 77, gold_obligation_missing 34, extra_obligation 1 (case_17 historical account_6523),
excluded 2 (object_19: no rule; tombstone_17: no category without the model); flags ACCOUNT_UNGROUNDED 20,
ACCOUNT_MULTI_GROUNDED 1, CONDITION_DEFAULTED 19, EMPTY_OBLIGATIONS 3
Live Jev category fallback (runs/usage_category_0011.jsonl, 3 calls ≈ 675 in / 178 out tokens each):
tombstone_17 → ACCOUNT_TOMBSTONE, export_1842 → USER_EXPORT, object_19 → none (top probability < 0.5 → excluded)
$ python code/evaluation/run_eval.py --split dev        # stub pipeline until 0012
status 0/20, F1 0.000 (unchanged)
```

All 518: only 3 discovered resources lack a record-derived category (catalog-linked, no observations), so the
fallback is a narrow hook.

## Scorer snapshot (dev)

| | Status acc | Account linkage | Step F1 | Seq exact |
|---|---|---|---|---|
| before (0010) | 0.000 | 7/20 (report) | 0.000 | 0.000 |
| after | 0.000 | 7/20 (report) | 0.000 | 0.000 |

## Notes

- `policy.py`: `required_state` (DELETE→ABSENT, REDACT→REDACTED, ANONYMIZE→ANONYMIZED, RETAIN→PRESENT,
  BACKUP_ARCHIVE→BLOCKED, DATA_FLOW→DISABLED); `condition` tri-state: "Always" → TRUE; SECURITY_AUDIT_LOG
  `retention_until` / LEGAL_HOLD_RECORD `retained_until` vs audit_at (latest eligible value) → TRUE/FALSE, missing →
  UNKNOWN; ACCOUNT_TOMBSTONE `account_status=DELETED` → TRUE; every other conditional rule (support message,
  attachment, analytics, email log, backup) → UNKNOWN ⇒ default action + CONDITION_DEFAULTED. FALSE ⇒ POLICY_UNDEFINED,
  no obligation, no inferred inverse action. `category_fallback`: one Jev Choice over the rule categories + DATA_FLOW,
  accepted only at probability ≥ 0.5.
- `obligations.py`: current state per required end state; REDACTED = no subject email/phone/name/hash in the latest
  present observation (user_id may remain; names also searched in free text); ANONYMIZED additionally requires no
  user_id link. [overnight] An absent record satisfies REDACTED/ANONYMIZED/DISABLED/BLOCKED (nothing left to expose,
  sync or restore) but never PRESENT. UNKNOWN never satisfies.
- `pipeline.assess`: grounded accounts (current + historical) and every other grounded discovered resource →
  category → rule → condition → state → obligation; diagnostics flags derived per §3.5.
