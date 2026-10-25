# Spec 0016 — packaging-and-interview: design

Contracts: `code/docs/TECHNICAL_DESIGN.md` §3. Data facts: §5.

- Zip from a clean `git ls-files code/` list plus generated reports; deterministic order.
- Secret scan regexes: `sk-`, `AIza`, long hex/base64 near `key|token|secret`.
