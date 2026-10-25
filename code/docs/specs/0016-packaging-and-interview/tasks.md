# Spec 0016 — packaging-and-interview: tasks

- [x] make_zip.py
- [x] README final
- [x] INTERVIEW_NOTES.md
- [x] dry-run zip and inspect listing
- [x] Update FEATURE_STATUS.md, status.md, this file; commit `spec 0016: <summary>`

## Validation commands

```bash
python code/tools/make_zip.py && python -c "import zipfile;z=zipfile.ZipFile('code.zip');print(len(z.namelist()));assert not any('dataset/' in n or n.endswith('.env') for n in z.namelist())" 
```
