# Spec 0014 — custom-eval-and-metamorphic: design

Contracts: `code/docs/TECHNICAL_DESIGN.md` §3. Data facts: §5.

- `code/evaluation/cases/<name>/{request.csv,overlay/,expected.csv,README.md}`.
- `code/evaluation/run_custom.py` copies dataset to `runs/tmp_<name>/`, applies overlay, runs pipeline with
  `--data-root`, compares with score.py.
- Requires `main.py --data-root` flag (add in this spec; update README).
