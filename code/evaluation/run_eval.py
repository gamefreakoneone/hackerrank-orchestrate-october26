"""Run the pipeline on the 32 samples and score it: python code/evaluation/run_eval.py [--split dev|holdout|all]."""
from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

EVALUATION_DIR = Path(__file__).resolve().parent
REPO_ROOT = EVALUATION_DIR.parents[1]
sys.path.insert(0, str(EVALUATION_DIR))

import score  # noqa: E402


def main(argv: list[str] | None = None) -> dict:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=["dev", "holdout", "all"], default="dev")
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "runs" / "sample.csv")
    parser.add_argument("pipeline_args", nargs="*", help="extra main.py flags after --, e.g. -- --offline")
    args = parser.parse_args(argv)
    subprocess.run([sys.executable, str(REPO_ROOT / "code" / "main.py"), "--cases", "sample", "--out", str(args.out),
                    *args.pipeline_args], check=True)
    gold_path = REPO_ROOT / "dataset" / "sample_output.csv"
    gold = score.read_rows(gold_path)
    result = score.score(score.read_rows(args.out), gold, score.split_case_ids(args.split, gold),
                         score.read_diagnostics(args.out.with_suffix(".diagnostics.jsonl")))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    markdown = score.render_markdown(result, f"Sample evaluation {stamp} (split={args.split})")
    report_path = REPO_ROOT / "runs" / f"score_{stamp}_{args.split}.md"
    report_path.write_text(markdown, encoding="utf-8")
    print(markdown.split("\n\n| Flag")[0])
    print(f"report: {report_path}")
    return result


if __name__ == "__main__":
    main(sys.argv[1:])
