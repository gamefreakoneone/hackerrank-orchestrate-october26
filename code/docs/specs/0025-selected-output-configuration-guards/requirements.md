# Spec 0025 — Selected-output configuration guards: requirements

**Status:** Not started. **Depends on:** 0024.
Read review M3 and spec 0021's selected-release constraints.

## Confirmed defect

`main.py` protects root output.csv from a nonempty --case selector only. A sample run validates against 32 sample
requests and may overwrite it; ablation configurations are also accepted. The finalizer's restrictions do not guard
direct main.py publication.

## Acceptance criteria

- Before inference, cache/ledger creation or output staging, reject selected-root-output requests using samples,
  --case selection, any ablation, ranked accounts, offline mode or a noncanonical custom data root.
  These remain supported with an explicit alternate --out; this restriction protects the selected submission path.
- The selected destination must use all canonical evaluation requests and default inference semantics. --no-cache
  is a permitted cache policy, not an ablation. Preserve existing default CLI behavior for legitimate full runs.
- Resolve path aliases before comparison, including relative paths and equivalent resolved destinations. Do not
  enforce the guard merely because a scratch file happens to be named output.csv.
- Rejection leaves output, matching diagnostics, manifest and existing selected bundle unchanged and performs no
  model call. Do not test this by risking the real selected output; use an isolated selected-path fixture.
- The finalizer explicitly rejects declared sample/partial/ablation/offline configurations as well as continuing
  to validate candidate coverage and hashes. Passing a fixture validator alone must not override configuration checks.
- Test a valid alternate-destination offline sample run through the actual CLI, and mock only provider/generation
  boundaries when testing legitimate full selected-output publication. Do not relabel offline provenance to claim
  a real live run occurred.
- Document exact safe sample/offline commands, failure messages and the selected-path contract in code/README.md.
- Run the full offline test suite after the settled changes and preserve selected artifacts. Report implementation
  readiness separately from the still-historical release, which requires authorized regeneration.

## Boundaries

Use a small shared configuration check where two real callers need it. No approval UI, global filesystem lock or new
deployment system. The documented mid-run revision and multi-file-rename risks remain separate follow-up questions;
do not claim this guard makes publication transactional.
