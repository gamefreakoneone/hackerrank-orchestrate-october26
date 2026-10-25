# Spec 0008 — llm-provider-layer: tasks

- [ ] providers.py
- [ ] jev.py
- [ ] hardening.py
- [ ] cache.py
- [ ] ledger.py
- [ ] models.yaml + pricing.yaml
- [ ] tests with fake provider (cache hit, repair retry, ledger sums)
- [ ] live smoke via 0001 script
- [ ] Update FEATURE_STATUS.md, status.md, this file; commit `spec 0008: <summary>`

## Validation commands

```bash
python -m pytest code/tests/test_llm_*.py -q
RUN_LIVE=1 python -m pytest code/tests/test_llm_live.py -q
python code/tools/smoke_providers.py
python code/evaluation/run_eval.py --split dev
```
