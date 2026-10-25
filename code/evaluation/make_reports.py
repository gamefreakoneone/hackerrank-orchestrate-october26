"""Render evaluation/evaluation_report.md and evaluation/usage_report.md from runs/ artifacts.

python code/evaluation/make_reports.py [--final-manifest runs/<run_id>.manifest.json]
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

EVALUATION_DIR = Path(__file__).resolve().parent
CODE_DIR = EVALUATION_DIR.parent
REPO_ROOT = CODE_DIR.parent
RUNS = REPO_ROOT / "runs"
sys.path.insert(0, str(CODE_DIR))
sys.path.insert(0, str(EVALUATION_DIR))

import score  # noqa: E402
from ghostaudit.llm.ledger import load_rows, summarize  # noqa: E402

GOLD = REPO_ROOT / "dataset" / "sample_output.csv"
ABLATIONS = [("default (submitted configuration)", "sample"),
             ("deterministic-only: no model calls (`--offline --no-cache`)", "ablation_deterministic"),
             ("no historical identifiers (`--ablate no-history`)", "ablation_no-history"),
             ("trust activity claims (`--ablate trust-claims`)", "ablation_trust-claims"),
             ("ranked guessed accounts, INCOMPLETE only (`--ungrounded-account-steps ranked`)", "ablation_ranked-accounts")]

IMPROVEMENTS = """| Spec / commit | Failure found | Change | Measured effect |
|---|---|---|---|
| 0007 `2cb0e29` | Six log formats; lookup key and resource id sit on different lines of one trace | one line parser per format, records = trace_id groups | sample identifier reach 76/111 (Phase-0b reference 77/111) |
| 0009 `04c26e4` | PNG screens were unread; decoy company emails visible on screens | Gemini extraction (cached) + regex/identity-universe revalidation | 23 PNG records; none of the 8 previously unreachable resources appears in a PNG (reach stays 103/111) |
| 0010 `f63f611` | `cache_lookup result=miss` merged into a trace was read as "record absent" (case_15 audit_record_1596) | infrastructure lines excluded from trace records | state agreement 99 → 104/111 (with the next two fixes) |
| 0010 `f63f611` | readback `*_read_completed` events not recognised as presence (case_03, case_18) | completed reads count as presence | gold-cited proofs 71 → 75/75 |
| 0010 `f63f611` | a later primary-only inventory overrode a replica that still held the account (case_05 replica drift) | omission must cover the replica where the record was last seen | case_05 PRESENT with evidence_54, as gold |
| 0012 `14df3a9` | generic snapshots claimed coverage of collections absent from the whole file (tombstone_17 "absent") | coverage only for collections present in that snapshot | no score change; removes an unsupported absence proof |
| 0013 `0623153` | negated requests ("not asking for deletion") contain deletion words | keyword check is a cross-check only; disagreements adjudicated by Azure | 10/10 non-deletion requests and 32/32 sample deletions classified correctly |
| 0010–0012 (kept) | 20/32 samples (351/518) have no grounded subject→account link | **not changed**: ranked guesses stay in diagnostics (contract) | status capped at the conditional bound 23/32; see the ranked-account ablation |
"""


def table(rows: list[list[str]], header: list[str]) -> str:
    return "\n".join(["| " + " | ".join(header) + " |", "|" + "---|" * len(header),
                      *["| " + " | ".join(map(str, r)) + " |" for r in rows]])


def score_file(name: str, split: str) -> dict | None:
    path = RUNS / f"{name}.csv"
    if not path.is_file():
        return None
    gold = score.read_rows(GOLD)
    return score.score(score.read_rows(path), gold, score.split_case_ids(split, gold),
                       score.read_diagnostics(path.with_suffix(".diagnostics.jsonl")))


def guessed_link_accuracy(name: str) -> str:
    diagnostics = score.read_diagnostics(RUNS / f"{name}.diagnostics.jsonl")
    gold = score.read_rows(GOLD)
    outcomes = Counter()
    for case_id, record in diagnostics.items():
        guess = record.get("guessed_account")
        if guess:
            gold_accounts = {s["resource_id"] for s in gold[case_id][1] if s["system_id"] == "account_service"}
            outcomes["right" if guess in gold_accounts else "wrong"] += 1
    return f"{outcomes['right']} right / {outcomes['wrong']} wrong guesses"


def metric_row(label: str, result: dict) -> list[str]:
    t = result["totals"]
    return [label, f"{result['status_accuracy']:.3f} ({t.get('status_ok', 0)}/{result['cases']})",
            f"{result['account_linkage'].get('correct', 0)}/{result['cases']}",
            f"{result['step_precision']:.3f} / {result['step_recall']:.3f} / {result['step_f1']:.3f}",
            f"{result['field_accuracy']['evidence_id']:.3f}", f"{result['field_accuracy']['step_no']:.3f}",
            f"{result['sequence_exact']:.3f} ({t.get('sequence_ok', 0)}/{result['cases']})", f"{result['mean_lcs']:.3f}"]


def output_distribution(path: Path) -> Counter:
    with path.open(encoding="utf-8", newline="") as handle:
        return Counter(r["deletion_status"] for r in csv.DictReader(handle))


def evaluation_report(manifest: dict) -> str:
    final_output = Path(manifest["args"]["out"])
    final_diagnostics = score.read_diagnostics(Path(manifest["diagnostics"]))
    flags = Counter(f for d in final_diagnostics.values() for f in d.get("flags", []))
    links = Counter(d["account_link"]["via"] for d in final_diagnostics.values() if "account_link" in d)
    splits = {split: score_file("sample", split) for split in ("dev", "holdout", "all")}
    header = ["Run", "Status acc", "Account linkage", "Step P / R / F1", "evidence_id acc", "step_no acc",
              "Sequence exact", "Mean LCS"]
    custom = (RUNS / "custom" / "results.md").read_text(encoding="utf-8") if (RUNS / "custom" / "results.md").is_file() \
        else "_custom results not found: run `python code/evaluation/run_custom.py`_"
    metamorphic = subprocess.run([sys.executable, "-m", "pytest", str(CODE_DIR / "tests" / "test_metamorphic.py"), "-q"],
                                 capture_output=True, text=True, cwd=REPO_ROOT).stdout.strip().splitlines()[-1]
    all_split = splits["all"]
    per_field = all_split["field_accuracy"]
    ablation_rows = []
    for label, name in ABLATIONS:
        result = score_file(name, "all")
        if result is not None:
            row = metric_row(label, result)
            if name == "ablation_ranked-accounts":
                row[2] = f"{row[2]} grounded; {guessed_link_accuracy(name)}"
            ablation_rows.append(row)
    full_ablations = []
    for label, name in [("default", Path(manifest["args"]["out"]).stem)] + \
            [(l, f"all_{n.removeprefix('ablation_')}") for l, n in ABLATIONS[1:]]:
        path = final_output if label == "default" else RUNS / f"{name}.csv"
        if path.is_file():
            distribution = output_distribution(path)
            full_ablations.append([label if label != "default" else "default (submitted output)",
                                   distribution["COMPLETE"], distribution["INCOMPLETE"], distribution["NOT_APPLICABLE"]])
    return f"""# Evaluation report — Ghost Data Still Exists

Produced by `python code/evaluation/make_reports.py` from the artifacts of the selected final run
(`{manifest['run_id']}`, code revision `{manifest['git_revision']}`, output sha256 `{manifest['output_sha256']}`).

**Read this first.** The 32 public samples were inspected while designing the system (Phase 0), so every sample number
below is a **regression-set** result, not untouched validation; the frozen dev (20) / holdout (12) split is reported
separately but both parts were inspected. The custom and metamorphic cases were written around known risks and are
**custom validation**, not a holdout. No untouched holdout exists, and nothing here measures hidden-answer accuracy.

## 1. Sample regression set (default configuration)

{table([metric_row(f"{split} ({splits[split]['cases']} cases)", splits[split]) for split in ("dev", "holdout", "all")], header)}

- **Case-level deletion-status accuracy:** {all_split['status_accuracy']:.3f} on all 32 samples. All misses are gold-COMPLETE
  cases whose account has no grounded link (ACCOUNT_UNGROUNDED keeps them INCOMPLETE by design); 23/32 is exactly the
  conditional upper bound recorded before implementation.
- **Account-linkage accuracy (separate metric):** {all_split['account_linkage']} — precision on grounded links
  {all_split['account_linkage_precision']:.3f}; the remaining cases have no grounded link in the eligible evidence.
- **Step-level accuracy** on keys (operation, system_id, resource_id): precision {all_split['step_precision']:.3f}, recall
  {all_split['step_recall']:.3f}, F1 {all_split['step_f1']:.3f} ({all_split['totals'].get('matched', 0)} matched of
  {all_split['totals'].get('pred_steps', 0)} predicted / {all_split['totals'].get('gold_steps', 0)} gold steps).
- **Field-level accuracy on matched steps:** phase {per_field['phase']:.3f}, state {per_field['state']:.3f}, evidence_id
  {per_field['evidence_id']:.3f}, step_no {per_field['step_no']:.3f}. evidence_id differences are verification steps of
  gold-COMPLETE cases we keep INCOMPLETE (empty evidence_id by contract); step_no shifts follow from missing steps.
- **Sequence accuracy:** exact match {all_split['sequence_exact']:.3f}; mean normalized LCS {all_split['mean_lcs']:.3f}.
  Every sample whose account link is grounded has an exactly matching plan.
- Blocker / diagnostic flags on samples: {json.dumps(all_split['flag_counts'])}.

## 2. Custom validation cases (participant-created, not a holdout)

Eight cases (nine requests) under `code/evaluation/cases/`, each with an overlay on a temporary copy of `dataset/`, an
expected output written from the rules and committed before the first run (`d33daa7`), and a rationale README.

{custom}

## 3. Metamorphic tests

`code/tests/test_metamorphic.py` (current result: `{metamorphic}`): a post-cutoff audit row per subject leaves every output
unchanged; shuffling the rows of every CSV leaves outputs unchanged; adding an unrelated user's identity and evidence
leaves outputs unchanged; moving `evidence_54` after every audit_at removes it from all citations and changes only the
cases that used it as proof, link or snapshot-omission candidate.

## 4. Ablations (samples, all 32)

{table(ablation_rows, header)}

Notes: the deterministic-only run uses the keyword intent check (marked provisional) and has no PNG facts or category
fallback. The ranked-account ablation plans the top-ranked guessed account in INCOMPLETE output only (it can never make a
case COMPLETE); it is never the submitted configuration. Trust-claims injects SUCCESS operational claims as if they were
observations; on these samples evidence captured after the claims dominates, so only proofs change.

Full-dataset status distribution per configuration (518 requests, no answers available):

{table(full_ablations, ["Configuration", "COMPLETE", "INCOMPLETE", "NOT_APPLICABLE"])}

## 5. Final run diagnostics (518 requests)

- Status distribution: {dict(output_distribution(final_output))}.
- Account link: {dict(links)} (non-deletion requests have no link).
- Flags: {dict(sorted(flags.items()))}.

## 6. Failures found and improvements made

{IMPROVEMENTS}
"""


def usage_report(manifest: dict) -> str:
    rows = load_rows(Path(manifest["usage_ledger"]))
    summary = summarize(rows)
    requests = manifest["rows"]
    tasks = defaultdict(Counter)
    for row in rows:
        if not row["cached"]:
            tasks[(row["provider"], row["model"])][row["task"]] += 1
    lines = []
    for (provider, model), totals in summary["per_model"].items():
        tokens = totals["input_tokens"] + totals["output_tokens"]
        cost = totals["cost_usd"]
        lines.append([provider, model, ", ".join(f"{t} {n}" for t, n in sorted(tasks[(provider, model)].items())),
                      totals["calls"], totals["attempts"], totals["cached_calls"], totals["input_tokens"],
                      totals["output_tokens"], tokens, f"{tokens / requests:.1f}",
                      "n/a" if cost is None else f"${cost:.6f}", "n/a" if cost is None else f"${cost / requests:.8f}"])
    overall = summary["overall"]
    overall_tokens = overall["input_tokens"] + overall["output_tokens"]
    cost = overall["cost_usd"]
    lines.append(["**overall**", "", "", overall["calls"], overall["attempts"], overall["cached_calls"],
                  overall["input_tokens"], overall["output_tokens"], overall_tokens, f"{overall_tokens / requests:.1f}",
                  "n/a" if cost is None else f"${cost:.6f}", "n/a" if cost is None else f"${cost / requests:.8f}"])
    pricing = (CODE_DIR / "config" / "pricing.yaml").read_text(encoding="utf-8")
    return f"""# Usage report — final full-dataset run

Run `{manifest['run_id']}` (code revision `{manifest['git_revision']}`), the cold-cache run that produced the submitted
`output.csv` (sha256 `{manifest['output_sha256']}`): `{' '.join(['python code/main.py', '--cases', manifest['args']['cases'], '--no-cache' if manifest['args']['no_cache'] else ''])}`
over {requests} requests. Source: usage ledger `{Path(manifest['usage_ledger']).relative_to(REPO_ROOT)}` (one row per
structured call). `--no-cache` skips cache reads, so every call below was a real model call.

{table(lines, ["Provider", "Model", "Calls by task", "Calls", "Attempts (incl. repair)", "Cached", "Input tokens",
               "Output tokens", "Total tokens", "Avg tokens / request", "Est. cost", "Est. cost / request"])}

- Averages divide by all {requests} requests (most requests make exactly one Jev intent call; PNG extraction is 11 calls
  shared by the whole run; Azure is called only when the intent decision table needs adjudication).
- **Costs are estimates.** No official price page for these model ids was found; the prices below come from third-party
  trackers (recorded with their sources in `code/config/pricing.yaml`). Gemini output tokens include reasoning tokens.

```yaml
{pricing.strip()}
```
"""


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--final-manifest", type=Path, default=None)
    args = parser.parse_args(argv)
    manifest_path = args.final_manifest or max(RUNS.glob("output_candidate_*.manifest.json"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    (EVALUATION_DIR / "evaluation_report.md").write_text(evaluation_report(manifest), encoding="utf-8")
    (EVALUATION_DIR / "usage_report.md").write_text(usage_report(manifest), encoding="utf-8")
    print(f"wrote evaluation_report.md and usage_report.md from {manifest_path.name}")


if __name__ == "__main__":
    main()
