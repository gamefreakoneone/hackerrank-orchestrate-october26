# Spec 0024 — Final artifact hash verification: status

**Status:** Not started
**Depends on:** completed and remotely published 0023
**Working/push branch:** `claude/specs-0017-0021-5s3kpe`
**Audited baseline:** `88a357ea152601aeca3ce5cc98e0fd764597b1c6`
**Implementation/publication:** not started.

## Evidence available before implementation

The actual loader accepted both wrong-hash counterexamples in memory. The pinned output/diagnostics/ledger hashes
matched the manifest, and both intact reports rendered byte-identically through their target functions. No actual
report CLI or clean-room packaging test was run by the reviewer.

## Scorer snapshot

| When / split | Revision / configuration | Status accuracy | Account linkage | Step F1 | Sequence exact |
|---|---|---|---|---|---|
| Before / dev | not measured; planned offline/no-cache after 0023 | not measured | not measured | not measured | not measured |
| After / dev | not measured; same configuration required | not measured | not measured | not measured | not measured |

## Checks and publication

- CLI failure regressions: not run for this spec.
- Preserved-bundle CLI rebuild and byte comparison: not measured.
- Implementation SHA / verified remote: record after execution.
