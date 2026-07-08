"""
evaluate_comparison.py
======================
Compare temperature settings on the same dataset using the full agent pipeline.
"""

import argparse
import csv
import json
import os
import warnings

warnings.filterwarnings("ignore", category=FutureWarning)

import google.generativeai as genai
from dotenv import load_dotenv

from evaluation.config import (
    DEFAULT_AGE,
    DEFAULT_GENDER,
    DEFAULT_LANGUAGE,
    DEFAULT_COMPARISON_COUNT,
    EVAL_MODEL,
    REAL_WORLD_CASES_CSV,
)
from evaluation.metrics import calculate_readability, validate_fhir_bundle
from evaluation.stats import format_mean_std, summarize
from evaluate_hallucination import evaluate_case
from utils.agent import run_agent

load_dotenv()


def get_api_key():
    key = os.environ.get("GEMINI_API_KEY")
    if not key or key in ("PASTE_YOUR_KEY_HERE", "get_your_free_key_from_aistudio.google.com"):
        print("ERROR: GEMINI_API_KEY required in .env")
        return None
    return key


def run_comparison_benchmark(
    input_file=REAL_WORLD_CASES_CSV,
    count=DEFAULT_COMPARISON_COUNT,
    output_md="comparison_results.md",
):
    api_key = get_api_key()
    if not api_key:
        return

    genai.configure(api_key=api_key)

    cases = []
    with open(input_file, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cases.append(row)
            if len(cases) >= count:
                break

    if not cases:
        print(f"No cases in {input_file}")
        return

    configs = [
        {"name": "Deterministic (Temp 0.0)", "temp": 0.0},
        {"name": "Exploratory (Temp 0.7)", "temp": 0.7},
    ]

    results = {}
    print(f"Comparison benchmark | n={len(cases)} | input={input_file}")

    for config in configs:
        name, temp = config["name"], config["temp"]
        print(f"\nConfiguration: {name}")

        gen_config = genai.types.GenerationConfig(
            temperature=temp, response_mime_type="application/json"
        )
        model = genai.GenerativeModel(EVAL_MODEL, generation_config=gen_config)

        hal_list, grade_list, ease_list, fhir_list = [], [], [], []
        successful = 0

        for idx, case in enumerate(cases):
            gt = case.get("ground_truth_report", "").strip()
            if not gt:
                continue
            print(f"  Case {idx + 1}/{len(cases)}...", end=" ", flush=True)

            extracted = {"type": "text", "content": gt}
            try:
                raw = run_agent(DEFAULT_AGE, DEFAULT_GENDER, DEFAULT_LANGUAGE, extracted, model, skip_routing=True)
                if "error" in raw:
                    print("ERROR")
                    continue
                print("OK")
                eval_res = evaluate_case(gt, json.dumps(raw))
                text = " ".join(
                    [
                        str(raw.get("health_status_reason", "")),
                        str(raw.get("age_specific_context", "")),
                    ]
                    + (raw.get("foods_to_eat") or [])
                    + (raw.get("foods_to_avoid") or [])
                )
                readability = calculate_readability(text)
                fhir_score, _ = validate_fhir_bundle(raw.get("fhir_bundle"))

                hal_list.append(eval_res.get("hallucination_score", 0.0))
                grade_list.append(readability["flesch_kincaid_grade"])
                ease_list.append(readability["flesch_reading_ease"])
                fhir_list.append(fhir_score)
                successful += 1
            except Exception as e:
                print(f"EXCEPTION: {e}")

        results[name] = {
            "avg_hallucination": summarize(hal_list)["mean"],
            "formatted_faithfulness": format_mean_std(hal_list),
            "avg_grade_level": summarize(grade_list)["mean"],
            "formatted_grade": format_mean_std(grade_list),
            "avg_readability_ease": summarize(ease_list)["mean"],
            "formatted_ease": format_mean_std(ease_list),
            "avg_fhir_validation": summarize(fhir_list)["mean"],
            "formatted_fhir": format_mean_std(fhir_list),
            "successful_runs": successful,
            "total_cases": len(cases),
        }

        print(f"  Faithfulness: {results[name]['formatted_faithfulness']}")
        print(f"  FK Grade:     {results[name]['formatted_grade']}")

    report_md = "# Model Configuration Benchmark\n\n"
    report_md += f"Dataset: `{input_file}` (N={len(cases)})\n\n"
    report_md += "| Configuration | Faithfulness (0-10) | FK Grade | Reading Ease | FHIR Compliance | Cases |\n"
    report_md += "| --- | --- | --- | --- | --- | --- |\n"
    for name, m in results.items():
        report_md += (
            f"| {name} | {m['formatted_faithfulness']} | {m['formatted_grade']} | "
            f"{m['formatted_ease']} | {m['formatted_fhir']} | {m['successful_runs']}/{m['total_cases']} |\n"
        )

    with open(output_md, "w", encoding="utf-8") as f:
        f.write(report_md)
    with open("comparison_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\nSaved: {output_md}, comparison_results.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=REAL_WORLD_CASES_CSV)
    parser.add_argument("--count", type=int, default=DEFAULT_COMPARISON_COUNT)
    args = parser.parse_args()
    run_comparison_benchmark(args.input, args.count)
