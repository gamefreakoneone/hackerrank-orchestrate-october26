# Spec 0015 — full-run-ablations-reports: design

Contracts: `code/docs/TECHNICAL_DESIGN.md` §3. Data facts: §5.

- `code/evaluation/make_reports.py` renders both Markdown files from `runs/` artifacts.
- Ablation flags: `--ablate no-history|trust-claims` in main.py (evaluation only).
- The 12-case split is reported separately but not called untouched validation.
