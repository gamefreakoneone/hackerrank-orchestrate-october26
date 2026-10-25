# Spec 0001 — scaffold-env-logging: tasks

- [ ] Pin `code/requirements.txt`
- [ ] Write `code/.env.example`
- [ ] Write `code/README.md` skeleton
- [ ] Implement `code/main.py` stub + `ghostaudit/config.py`
- [ ] Implement `code/tools/smoke_providers.py`
- [ ] Add `code/tests/test_main_stub.py` (518 rows, header, numeric order, valid JSON)
- [ ] Update FEATURE_STATUS.md, status.md, this file; commit `spec 0001: <summary>`

## Validation commands

```bash
pip install -r code/requirements.txt
python code/main.py && python -c "import csv;r=list(csv.DictReader(open('output.csv')));assert len(r)==518;print('rows',len(r))"
python -m pytest code/tests -q
python code/tools/smoke_providers.py
```
