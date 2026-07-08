"""
run_all_evaluations.py
======================
Run the full evaluation suite in order and write a combined summary.

Usage:
  python run_all_evaluations.py
  python run_all_evaluations.py --count 10 --skip-ablation
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime


def run_step(name: str, cmd: list[str]) -> bool:
    print("\n" + "#" * 60)
    print(f"# {name}")
    print("#" * 60)
    result = subprocess.run(cmd, cwd=os.path.dirname(os.path.abspath(__file__)) or ".")
    ok = result.returncode == 0
    print(f"{'OK' if ok else 'FAILED'}: {name}")
    return ok


def main():
    parser = argparse.ArgumentParser(description="Run full evaluation suite.")
    parser.add_argument("--count", type=int, default=10, help="Cases per pipeline/ablation run")
    parser.add_argument("--input", default="real_world_cases.csv")
    parser.add_argument("--skip-download", action="store_true")
    parser.add_argument("--skip-pipeline", action="store_true")
    parser.add_argument("--skip-ablation", action="store_true")
    parser.add_argument("--skip-bias", action="store_true")
    parser.add_argument("--skip-robustness", action="store_true")
    args = parser.parse_args()

    py = sys.executable
    results = {"started_at": datetime.now().isoformat(), "steps": {}}

    if not args.skip_download and not os.path.exists(args.input):
        ok = run_step("Download PMC dataset", [py, "download_pmc.py", "--count", str(max(args.count, 50))])
        results["steps"]["download_pmc"] = ok
        if not ok:
            print("WARNING: Dataset download failed. Using evaluation_cases.csv fallback if available.")
            if os.path.exists("evaluation_cases.csv"):
                args.input = "evaluation_cases.csv"

    if not args.skip_pipeline:
        ok = run_step(
            "End-to-end pipeline evaluation",
            [py, "evaluate_pipeline.py", "--input", args.input, "--count", str(args.count)],
        )
        results["steps"]["pipeline"] = ok
        if ok and os.path.exists("evaluation_summary.json"):
            with open("evaluation_summary.json", encoding="utf-8") as f:
                results["pipeline_summary"] = json.load(f)
            run_step(
                "Export clinician review sheet",
                [py, "clinician_review.py", "export", "--input", "evaluation_results.csv"],
            )

    if not args.skip_ablation:
        ok = run_step(
            "Ablation study",
            [py, "evaluate_ablation.py", "--input", args.input, "--count", str(args.count)],
        )
        results["steps"]["ablation"] = ok

    if not args.skip_bias:
        ok = run_step("Bias / fairness evaluation", [py, "evaluate_bias.py"])
        results["steps"]["bias"] = ok

    if not args.skip_robustness:
        ok = run_step("Visual robustness evaluation", [py, "evaluate_robustness.py"])
        results["steps"]["robustness"] = ok

    results["finished_at"] = datetime.now().isoformat()
    with open("full_evaluation_report.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 60)
    print("FULL EVALUATION SUITE FINISHED")
    print("Outputs:")
    print("  - evaluation_results.csv")
    print("  - evaluation_summary.json")
    print("  - ablation_results.json")
    print("  - clinician_review_sheet.csv (for doctor ratings)")
    print("  - fairness_evaluation_results.md")
    print("  - robustness_evaluation_results.md")
    print("  - full_evaluation_report.json")
    print("=" * 60)


if __name__ == "__main__":
    main()
