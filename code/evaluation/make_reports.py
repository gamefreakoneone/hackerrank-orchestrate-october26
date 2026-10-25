"""Render evaluation_report.md and usage_report.md from preserved, hashed artifacts. No model or provider call.

python code/evaluation/make_reports.py [--final-manifest code/evaluation/final_run/manifest.json]
    [--evaluation-inputs PATH/evaluation_inputs.json] [--report-output-directory DIR] [--allow-revision-mismatch]

The final-run manifest names the selected output, diagnostics and usage ledger; the evaluation inputs
(written by capture_inputs.py) name the sample, ablation, custom, discovery and test results with SHA-256 values.
A missing, altered or mismatched input stops the build with an explicit error (exit code 1).
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

EVALUATION_DIR = Path(__file__).resolve().parent
CODE_DIR = EVALUATION_DIR.parent
REPO_ROOT = CODE_DIR.parent
sys.path.insert(0, str(CODE_DIR))
sys.path.insert(0, str(EVALUATION_DIR))

import score  # noqa: E402
from capture_inputs import SAMPLE_CONFIGURATIONS  # noqa: E402
from ghostaudit.llm.ledger import load_rows, summarize  # noqa: E402
from ghostaudit.provenance import sha256_of  # noqa: E402

PRICING_PATH = CODE_DIR / "config" / "pricing.yaml"
DISCOVERY_RECALL_TARGET = 0.85     # spec 0010 acceptance target for sample resource recall
ABLATION_LABELS = {
    "deterministic": "deterministic-only: no model calls (`--offline --no-cache`)",
    "no-history": "no historical identifiers (`--ablate no-history`)",
    "trust-claims": "trust activity claims (`--ablate trust-claims`)",
    "ranked-accounts": "ranked guessed accounts, INCOMPLETE only (`--ungrounded-account-steps ranked`)",
}

HISTORICAL_IMPROVEMENTS = """Recorded at the commit that made each change (sample regression set; "oracle-assisted" = the check was
given the gold resource ids and operations, so it measures a component, not end-to-end discovery):

| Spec / commit | Failure found | Change | Measured effect (as recorded then) |
|---|---|---|---|
| 0007 `2cb0e29` | Six log formats; lookup key and resource id sit on different lines of one trace | one line parser per format, records = trace_id groups | sample identifier reach 76/111 |
| 0009 `04c26e4` | PNG screens were unread; decoy company emails visible on screens | Gemini extraction (cached) + regex/identity-universe revalidation | 23 PNG records; none of the 8 unreachable resources appears in a PNG |
| 0010 `f63f611` | `cache_lookup result=miss` inside a trace read as "record absent"; completed reads not counted as presence | infrastructure lines excluded; completed reads count as presence | oracle-assisted state agreement 99 → 104/111, proofs 71 → 75/75 |
| 0012 `14df3a9` | generic snapshots claimed coverage of collections absent from the whole file | coverage only for collections present in that snapshot | no score change; removes an unsupported absence proof |
| 0013 `0623153` | negated requests contain deletion words | keyword check is a cross-check only; disagreements adjudicated by Azure | 10/10 non-deletion requests and 32/32 sample deletions classified correctly |
| 0017 `4f2a05a` | a newer primary-only read or clean record hid an uncleared replica; a newer package of an older read overwrote newer state | state per storage copy, violation wins; observation-time ordering; bundle omissions scoped to their subjects | sample outputs unchanged; full-dataset 3 obligations changed (0 COMPLETE → INCOMPLETE); oracle-assisted state 103/111 |
| 0018 `b0c7f27` | absence satisfied REDACT / ANONYMIZE / retained-backup obligations | separate preservation predicate, REQUIRED_RECORD_MISSING blocker | sample outputs unchanged; 0 full-dataset changes |
| 0019 `52a1854` | 34 sample resources ungrounded | investigation only: no defensible pre-cutoff link exists (`DISCOVERY_GAP_REVIEW.md`) | recall unchanged; the 0010 ≥85% target stays unmet |
| 0020 | reports claimed every grounded sample had an exact plan and depended on ignored `runs/` files | claims derived from per-case scores; hashed evaluation inputs; explicit input errors | this report |
"""


def fail(message: str) -> None:
    raise SystemExit(f"make_reports: {message}")


def table(rows: list[list], header: list[str]) -> str:
    return "\n".join(["| " + " | ".join(header) + " |", "|" + "---|" * len(header),
                      *["| " + " | ".join(map(str, r)) + " |" for r in rows]])


def verified_artifact(directory: Path, relative_path: str, expected_sha256: str, role: str) -> Path:
    path = directory / relative_path
    if not path.is_file():
        fail(f"{role} is missing: {path}")
    if sha256_of(path) != expected_sha256:
        fail(f"{role} {path} does not match its recorded sha256 (artifact changed after capture)")
    return path


def load_final_run(manifest_path: Path, repository_root: Path) -> dict:
    if not manifest_path.is_file():
        fail(f"final-run manifest is missing: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    output = repository_root / "output.csv"
    if not output.is_file() or sha256_of(output) != manifest["output_sha256"]:
        fail(f"{output} does not match the selected final run {manifest['run_id']} (sha256 differs or file missing)")
    for role in ("diagnostics", "usage_ledger"):
        if not (repository_root / manifest[role]).is_file():
            fail(f"final-run {role} is missing: {repository_root / manifest[role]}")
    output_case_ids = set(score.read_rows(output))
    diagnostics = score.read_diagnostics(repository_root / manifest["diagnostics"])
    if set(diagnostics) != output_case_ids:
        fail("final-run diagnostics do not cover exactly the output's case ids")
    return {"manifest": manifest, "output": output, "diagnostics": diagnostics,
            "usage_rows": load_rows(repository_root / manifest["usage_ledger"])}


def load_evaluation_inputs(inputs_path: Path, gold: dict) -> dict:
    if not inputs_path.is_file():
        fail(f"evaluation inputs are missing: {inputs_path} (run code/evaluation/capture_inputs.py)")
    inputs = json.loads(inputs_path.read_text(encoding="utf-8"))
    directory = inputs_path.parent
    missing_keys = sorted({"code_revision", "captured_at", "provider_configuration", "sample_runs",
                           "custom_results"} - set(inputs))
    if missing_keys:
        fail(f"evaluation inputs {inputs_path} lack required fields {missing_keys}")
    if "default" not in inputs["sample_runs"]:
        fail("evaluation inputs have no default sample run (required)")
    runs = {}
    for name, entry in sorted(inputs["sample_runs"].items()):
        if SAMPLE_CONFIGURATIONS.get(name) != entry["pipeline_args"]:
            fail(f"sample run {name!r} declares {entry['pipeline_args']}, expected {SAMPLE_CONFIGURATIONS.get(name)}")
        predictions = score.read_rows(verified_artifact(directory, entry["predictions"], entry["predictions_sha256"],
                                                        f"{name} predictions"))
        diagnostics = score.read_diagnostics(verified_artifact(directory, entry["diagnostics"],
                                                               entry["diagnostics_sha256"], f"{name} diagnostics"))
        if set(predictions) != set(gold) or set(diagnostics) != set(gold):
            fail(f"{name} predictions/diagnostics do not cover exactly the {len(gold)} sample case ids")
        runs[name] = {"predictions": predictions, "diagnostics": diagnostics, "model_calls": entry.get("model_calls")}
    custom_entry = inputs["custom_results"]
    custom = json.loads(verified_artifact(directory, custom_entry["path"], custom_entry["sha256"],
                                          "custom results").read_text(encoding="utf-8"))
    discovery = None
    if inputs.get("discovery_report"):
        entry = inputs["discovery_report"]
        discovery = json.loads(verified_artifact(directory, entry["path"], entry["sha256"],
                                                 "discovery report").read_text(encoding="utf-8"))
    return {**inputs, "runs": runs, "custom": custom, "discovery": discovery, "path": inputs_path}


def metric_row(label: str, result: dict) -> list[str]:
    t = result["totals"]
    return [label, f"{result['status_accuracy']:.3f} ({t.get('status_ok', 0)}/{result['cases']})",
            f"{result['account_linkage'].get('correct', 0)}/{result['cases']}",
            f"{result['step_precision']:.3f} / {result['step_recall']:.3f} / {result['step_f1']:.3f}",
            f"{result['field_accuracy']['evidence_id']:.3f}", f"{result['field_accuracy']['step_no']:.3f}",
            f"{result['sequence_exact']:.3f} ({t.get('sequence_ok', 0)}/{result['cases']})", f"{result['mean_lcs']:.3f}"]


def evidence_mismatches(predictions: dict, gold: dict) -> tuple[int, int]:
    """(matched steps citing different evidence, of which in gold-COMPLETE cases predicted INCOMPLETE)."""
    total = in_unproven_complete = 0
    for case_id, (gold_status, gold_steps) in gold.items():
        predicted_status, predicted_steps = predictions[case_id]
        predicted_by_key = {score.step_key(s): s for s in predicted_steps}
        for step in gold_steps:
            other = predicted_by_key.get(score.step_key(step))
            if other is not None and other["evidence_id"] != step["evidence_id"]:
                total += 1
                in_unproven_complete += gold_status == "COMPLETE" and predicted_status == "INCOMPLETE"
    return total, in_unproven_complete


def guessed_link_accuracy(diagnostics: dict, gold: dict) -> str:
    outcomes = Counter()
    for case_id, record in diagnostics.items():
        if record.get("guessed_account"):
            gold_accounts = {s["resource_id"] for s in gold[case_id][1] if s["system_id"] == "account_service"}
            outcomes["right" if record["guessed_account"] in gold_accounts else "wrong"] += 1
    return f"{outcomes['right']} right / {outcomes['wrong']} wrong guesses"


def sample_claims(result: dict, predictions: dict, gold: dict) -> str:
    per_case, t = result["per_case"], result["totals"]
    misses = [c for c in per_case if not c["status_ok"]]
    unproven_complete = [c for c in misses if c["gold"] == "COMPLETE" and c["account"] == "ungrounded"]
    grounded = [c for c in per_case if c["account"] in ("correct", "wrong")]
    grounded_exact = [c for c in grounded if c["sequence_ok"]]
    mismatched, mismatched_unproven = evidence_mismatches(predictions, gold)
    field = result["field_accuracy"]
    return f"""- **Case-level deletion-status accuracy:** {t.get('status_ok', 0)}/{result['cases']} \
({result['status_accuracy']:.3f}). {len(misses)} status misses; {len(unproven_complete)} of them are gold-COMPLETE cases \
whose account has no grounded link (ACCOUNT_UNGROUNDED keeps them INCOMPLETE by contract).
- **Account linkage (separate metric):** {result['account_linkage']} over {result['cases']} cases; precision of grounded \
links {result['account_linkage_precision']:.3f}.
- **Step-level accuracy** on keys (operation, system_id, resource_id): precision {result['step_precision']:.3f} \
({t.get('matched', 0)}/{t.get('pred_steps', 0)} predicted steps), recall {result['step_recall']:.3f} \
({t.get('matched', 0)}/{t.get('gold_steps', 0)} gold steps), F1 {result['step_f1']:.3f}.
- **Field-level accuracy on the {t.get('matched', 0)} matched steps:** phase {field['phase']:.3f}, state \
{field['state']:.3f}, evidence_id {field['evidence_id']:.3f}, step_no {field['step_no']:.3f}. {mismatched} matched steps \
cite different evidence; {mismatched_unproven} of them are in gold-COMPLETE cases predicted INCOMPLETE (future \
verification steps carry an empty evidence_id by contract).
- **Sequence accuracy:** {t.get('sequence_ok', 0)}/{result['cases']} exact ({result['sequence_exact']:.3f}); mean \
normalized LCS {result['mean_lcs']:.3f}. {len(grounded_exact)} of the {len(grounded)} samples with a grounded account \
link have an exactly matching plan.
- Blocker / diagnostic flags (cases): {json.dumps(result['flag_counts'])}."""


def discovery_section(discovery: dict | None) -> str:
    if discovery is None:
        return "_Not measured in this bundle (no discovery report captured)._"
    found, total = map(int, discovery["resource_recall"].split("/"))
    verdict = "met" if found / total >= DISCOVERY_RECALL_TARGET else "**unmet**"
    return f"""End-to-end discovery on the samples (`code/tools/discovery_report.py`; gold is used only to score):
resource recall {discovery['resource_recall']} ({found / total:.1%}; spec 0010 target ≥ {DISCOVERY_RECALL_TARGET:.0%}: \
{verdict}), current accounts {discovery['account_recall']}, other resources {discovery['other_resource_recall']}, \
{discovery['extra_resources']} extra grounded resources, linkage precision {discovery['linkage_precision']}.
Miss causes (participant-visible evidence at each audit_at): {json.dumps(discovery['miss_causes'])}.
See `code/docs/DISCOVERY_GAP_REVIEW.md`."""


def custom_section(custom: dict) -> str:
    results = custom["results"]
    mark = lambda ok: "pass" if ok else "FAIL"
    rows = [[r["case"], r["case_id"], r["expected_status"], r["got_status"], mark(r["status_ok"]), mark(r["steps_ok"]),
             mark(r["flags_ok"]), mark(r["validator_ok"]), " ".join(r["flags"])] for r in results]
    passed = sum(all((r["status_ok"], r["steps_ok"], r["flags_ok"], r["validator_ok"])) for r in results)
    cases = len({r["case"] for r in results})
    return f"""{cases} cases ({len(results)} requests) under `code/evaluation/cases/`, each an overlay on a temporary copy of
`dataset/` with an expected output written from the rules and a rationale README{' (run offline)' if custom.get('offline') else ''}.
{passed}/{len(results)} requests fully pass.

{table(rows, ["case", "request", "expected", "got", "status", "steps", "flags", "validator", "flags seen"])}"""


def tests_section(test_results: list[dict] | None) -> str:
    if not test_results:
        return "_Not measured in this bundle (no recorded test run)._"
    return table([[t["name"], f"`{t['command']}`", t["exit_code"], t["summary"]] for t in test_results],
                 ["Suite", "Command", "Exit code", "Result"])


def evaluation_report(final: dict, inputs: dict, gold: dict, unified: bool) -> str:
    manifest = final["manifest"]
    default = inputs["runs"]["default"]
    splits = {split: score.score(default["predictions"], gold, score.split_case_ids(split, gold), default["diagnostics"])
              for split in ("dev", "holdout", "all")}
    header = ["Run", "Status acc", "Account linkage", "Step P / R / F1", "evidence_id acc", "step_no acc",
              "Sequence exact", "Mean LCS"]
    ablation_rows = []
    for name, label in ABLATION_LABELS.items():
        run = inputs["runs"].get(name)
        if run is None:
            ablation_rows.append([label, "not measured", "", "", "", "", "", ""])
            continue
        row = metric_row(label, score.score(run["predictions"], gold, score.split_case_ids("all", gold),
                                            run["diagnostics"]))
        if name == "ranked-accounts":
            row[2] = f"{row[2]} grounded; {guessed_link_accuracy(run['diagnostics'], gold)}"
        ablation_rows.append(row)
    flags = Counter(f for d in final["diagnostics"].values() for f in d.get("flags", []))
    links = Counter(d["account_link"]["via"] for d in final["diagnostics"].values() if "account_link" in d)
    with final["output"].open(encoding="utf-8", newline="") as handle:
        distribution = Counter(r["deletion_status"] for r in csv.DictReader(handle))
    provenance = ("The evaluation inputs and the final run come from the **same code revision**." if unified else
                  "**NOT a unified release:** the evaluation inputs and the selected final run come from different "
                  "code revisions. Sample metrics below describe the evaluation-input revision, not the code that "
                  "produced the selected output.")
    return f"""# Evaluation report — Ghost Data Still Exists

Built by `python code/evaluation/make_reports.py` from preserved artifacts (no model calls):
- selected final run `{manifest['run_id']}`, code revision `{manifest['git_revision']}`, output sha256 `{manifest['output_sha256']}`;
- evaluation inputs `{inputs['path'].name}` captured {inputs['captured_at']} at code revision `{inputs['code_revision']}`
  (provider keys present: {', '.join(inputs['provider_configuration']['provider_keys_present']) or 'none'}; default sample
  run model calls: {json.dumps(default['model_calls'])}).

{provenance}

**Read this first.** The 32 public samples were inspected while designing the system, so every sample number is a
**regression-set** result, not untouched validation; the dev (20) / holdout (12) split was inspected too. Custom and
metamorphic cases are **custom validation** written around known risks. No untouched holdout exists, and nothing here
measures hidden-answer accuracy.

## 1. Sample regression set (default configuration)

{table([metric_row(f"{split} ({splits[split]['cases']} cases)", splits[split]) for split in ("dev", "holdout", "all")], header)}

{sample_claims(splits['all'], default['predictions'], gold)}

## 2. Discovery coverage

{discovery_section(inputs['discovery'])}

## 3. Custom validation cases (participant-created, not a holdout)

{custom_section(inputs['custom'])}

## 4. Recorded test runs

`code/tests/test_metamorphic.py`: a post-cutoff audit row per subject, shuffled CSV rows and an unrelated user's identity
and evidence leave outputs unchanged; moving `evidence_54` after every audit_at changes only the cases that used it.

{tests_section(inputs.get('test_results'))}

## 5. Ablations (samples, all 32)

{table(ablation_rows, header)}

The deterministic-only run uses the keyword intent check and has no PNG facts or category fallback. The ranked-account
ablation plans the top-ranked guessed account in INCOMPLETE output only and is never the submitted configuration.
Trust-claims injects SUCCESS operational claims as if they were observations. Full-dataset ablations are not measured.

## 6. Selected final run diagnostics ({manifest['rows']} requests)

- Status distribution: {dict(sorted(distribution.items()))}.
- Account link: {dict(sorted(links.items()))} (non-deletion requests have no link).
- Flags: {dict(sorted(flags.items()))}.

## 7. Failures found and improvements made

{HISTORICAL_IMPROVEMENTS}"""


def usage_report(final: dict) -> str:
    manifest, rows = final["manifest"], final["usage_rows"]
    summary = summarize(rows)
    requests = manifest["rows"]
    tasks = defaultdict(Counter)
    for row in rows:
        if not row["cached"]:
            tasks[(row["provider"], row["model"])][row["task"]] += 1

    def cost_cells(cost):
        return ["n/a" if cost is None else f"${cost:.6f}", "n/a" if cost is None else f"${cost / requests:.8f}"]

    lines = []
    for (provider, model), totals in summary["per_model"].items():
        tokens = totals["input_tokens"] + totals["output_tokens"]
        lines.append([provider, model, ", ".join(f"{t} {n}" for t, n in sorted(tasks[(provider, model)].items())),
                      totals["calls"], totals["attempts"], totals["cached_calls"], totals["input_tokens"],
                      totals["output_tokens"], tokens, f"{tokens / requests:.1f}", *cost_cells(totals["cost_usd"])])
    overall = summary["overall"]
    overall_tokens = overall["input_tokens"] + overall["output_tokens"]
    lines.append(["**overall**", "", "", overall["calls"], overall["attempts"], overall["cached_calls"],
                  overall["input_tokens"], overall["output_tokens"], overall_tokens, f"{overall_tokens / requests:.1f}",
                  *cost_cells(overall["cost_usd"])])
    command = " ".join(["python code/main.py", "--cases", manifest["args"]["cases"],
                        *(["--no-cache"] if manifest["args"]["no_cache"] else [])])
    return f"""# Usage report — final full-dataset run

Run `{manifest['run_id']}` (code revision `{manifest['git_revision']}`), the run that produced the selected `output.csv`
(sha256 `{manifest['output_sha256']}`): `{command}` over {requests} requests. Source: usage ledger
`{manifest['usage_ledger']}` (one row per structured call; calls and tokens are reported exactly as recorded).
{'`--no-cache` skips cache reads, so every call below was a real model call.' if manifest['args']['no_cache'] else ''}

{table(lines, ["Provider", "Model", "Calls by task", "Calls", "Attempts (incl. repair)", "Cached", "Input tokens",
               "Output tokens", "Total tokens", "Avg tokens / request", "Est. cost", "Est. cost / request"])}

- Averages divide by all {requests} requests (most requests make one Jev intent call; PNG extraction is 11 calls shared by
  the whole run; Azure is called only when the intent decision table needs adjudication).
- **Costs are estimated and unverified.** No official price page for these model ids was found; the prices come from
  third-party trackers (sources in `code/config/pricing.yaml`). Gemini output tokens include reasoning tokens.

```yaml
{PRICING_PATH.read_text(encoding="utf-8").strip()}
```
"""


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--final-manifest", type=Path, default=EVALUATION_DIR / "final_run" / "manifest.json")
    parser.add_argument("--evaluation-inputs", type=Path, default=None,
                        help="default: the path named by the final manifest's evaluation_inputs field")
    parser.add_argument("--report-output-directory", type=Path, default=EVALUATION_DIR,
                        help="stage reports elsewhere without replacing the selected ones")
    parser.add_argument("--allow-revision-mismatch", action="store_true",
                        help="render a report labelled NOT a unified release when the input revisions differ")
    parser.add_argument("--repository-root", type=Path, default=REPO_ROOT,
                        help="root holding output.csv, dataset/sample_output.csv and the manifest's relative paths")
    args = parser.parse_args(argv)
    final = load_final_run(args.final_manifest, args.repository_root)
    inputs_path = args.evaluation_inputs
    if inputs_path is None:
        if "evaluation_inputs" not in final["manifest"]:
            fail("the final manifest names no evaluation_inputs; pass --evaluation-inputs PATH")
        inputs_path = args.repository_root / final["manifest"]["evaluation_inputs"]
    gold = score.read_rows(args.repository_root / "dataset" / "sample_output.csv")
    inputs = load_evaluation_inputs(inputs_path, gold)
    unified = inputs["code_revision"] == final["manifest"]["git_revision"]
    if not unified and not args.allow_revision_mismatch:
        fail(f"evaluation inputs revision {inputs['code_revision']} != final run revision "
             f"{final['manifest']['git_revision']}; pass --allow-revision-mismatch to stage a report labelled "
             "NOT a unified release")
    args.report_output_directory.mkdir(parents=True, exist_ok=True)
    (args.report_output_directory / "evaluation_report.md").write_text(evaluation_report(final, inputs, gold, unified),
                                                                       encoding="utf-8")
    (args.report_output_directory / "usage_report.md").write_text(usage_report(final), encoding="utf-8")
    print(f"wrote evaluation_report.md and usage_report.md to {args.report_output_directory}")


if __name__ == "__main__":
    main()
