# Spec 0003 — data-contracts-loaders: status

**Status:** Completed (2026-10-25, overnight run)

## Evidence

```text
$ python -m pytest code/tests/test_loaders.py code/tests/test_models.py -q
7 passed
```

Row counts asserted: requests 518, samples 32, identities 850, audit 306, activity 4011, rules 15, evidence 94.
Scorer metrics: not measured (scorer arrives in spec 0005).

## Notes

- `ghostaudit/models.py`: enums, `OP_ORDER` (= `Operation` declaration order), `OP_PHASE`, `OP_STATE`, request/CSV
  models, `Step`, `Obligation`, `case_key`. `Observation` and `SnapshotCoverage` live in
  `ghostaudit/evidence/model.py` per TECHNICAL_DESIGN §3.2/§3.3. `Obligation` is in `models.py` (obligations.py
  will import it) to keep all output-side contracts in one module.
- `Observation.fields` is a plain `dict` (pydantic frozen model; hashing not needed).
- `load_dataset(dataset_dir, sample=False)` takes the dataset directory (spec 0014's `--data-root` reuses it);
  asserts every manifest file exists; a test guards that `sample_output.csv` is never opened.
