# Spec 0004 — serializer-validator: tasks

- [x] serialize.py
- [x] validate.py
- [x] wire into main.py
- [x] tests incl. sample_output.csv passes, 8 mutation cases fail
- [x] Update FEATURE_STATUS.md, status.md, this file; commit `spec 0004: <summary>`

## Validation commands

```bash
python -m pytest code/tests/test_serialize.py code/tests/test_validate.py -q
python code/main.py && python -c "import sys;sys.path.insert(0,'code');from ghostaudit.validate import cli;cli()" 
```
