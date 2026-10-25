# Spec 0015 — full-run-ablations-reports: design

Contracts: `code/docs/TECHNICAL_DESIGN.md` §3. Data facts: §5.

- `code/evaluation/make_reports.py` renders both Markdown files from `runs/` artifacts.
- Ablation flags: `--ablate no-history|trust-claims` in main.py (evaluation only).
- Holdout is scored once here, not used for tuning.
