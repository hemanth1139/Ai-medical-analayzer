"""
evaluate_ablation.py
====================
Runs ablation baseline variants on the evaluation dataset and saves
ablation_results.json with mean ± std statistics.

Literature comparison values live in evaluation/literature_baselines.json
(reference only — not mixed into experimental results).

Usage:
  python evaluate_ablation.py
  python evaluate_ablation.py --count 10 --input real_world_cases.csv
"""

import argparse
import csv
import json
import re
import warnings

warnings.filterwarnings("ignore", category=FutureWarning)

import google.generativeai as genai
from dotenv import load_dotenv

from evaluation.config import (
    ABLATION_RESULTS_JSON,
    DEFAULT_ABLATION_COUNT,
    DEFAULT_AGE,
    DEFAULT_GENDER,
    DEFAULT_LANGUAGE,
    EVAL_MODEL,
    EVAL_TEMPERATURE,
    LITERATURE_BASELINES_PATH,
    REAL_WORLD_CASES_CSV,
)
from evaluation.metrics import calculate_readability, validate_fhir_bundle
from evaluation.stats import format_mean_std, summarize
from evaluate_hallucination import evaluate_case

load_dotenv()


def get_api_key():
    import os

    key = os.environ.get("GEMINI_API_KEY")
    if not key or key == "PASTE_YOUR_KEY_HERE":
        print("ERROR: Set GEMINI_API_KEY in your .env file first.")
        return None
    return key


def load_cases(path, count):
    cases = []
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cases.append(row)
            if len(cases) >= count:
                break
    return cases


def run_naive(model, report_text):
    prompt = (
        "You are a helpful medical assistant. "
        "Read the following medical report and explain it simply to the patient "
        "in plain English. Tell them what they should do next.\n\n"
        f"Report:\n{report_text}"
    )
    config = genai.types.GenerationConfig(temperature=EVAL_TEMPERATURE)
    response = model.generate_content(prompt, generation_config=config)
    return {"health_status_reason": response.text, "fhir_bundle": None}


def run_no_rag(model, report_text, age=DEFAULT_AGE, gender=DEFAULT_GENDER):
    from utils.builder import build_prompt
    from utils.privacy_guard import sanitize_input

    prompt = build_prompt(age, gender, DEFAULT_LANGUAGE, "typed medical document")
    prompt = re.sub(
        r"Below is your MEDICAL KNOWLEDGE BASE.*?-{10,}",
        "MEDICAL KNOWLEDGE BASE: [DISABLED FOR ABLATION TEST]\n" + "-" * 42,
        prompt,
        flags=re.DOTALL,
    )
    sanitized, pii_instr = sanitize_input(report_text, "text")
    if pii_instr:
        prompt += "\n\n" + pii_instr

    config = genai.types.GenerationConfig(
        temperature=EVAL_TEMPERATURE, response_mime_type="application/json"
    )
    response = model.generate_content([prompt, sanitized], generation_config=config)
    try:
        return json.loads(response.text)
    except Exception:
        return {"error": "JSON parse failed", "fhir_bundle": None}


def run_no_pii(model, report_text, age=DEFAULT_AGE, gender=DEFAULT_GENDER):
    from utils.builder import build_prompt

    prompt = build_prompt(age, gender, DEFAULT_LANGUAGE, "typed medical document")
    config = genai.types.GenerationConfig(
        temperature=EVAL_TEMPERATURE, response_mime_type="application/json"
    )
    response = model.generate_content([prompt, report_text], generation_config=config)
    try:
        return json.loads(response.text)
    except Exception:
        return {"error": "JSON parse failed", "fhir_bundle": None}


def run_no_agent(model, report_text, age=DEFAULT_AGE, gender=DEFAULT_GENDER):
    from utils.builder import build_prompt
    from utils.privacy_guard import sanitize_input

    prompt = build_prompt(
        age, gender, DEFAULT_LANGUAGE, "typed medical document", analysis_mode="text"
    )
    sanitized, pii_instr = sanitize_input(report_text, "text")
    if pii_instr:
        prompt += "\n\n" + pii_instr

    config = genai.types.GenerationConfig(
        temperature=EVAL_TEMPERATURE, response_mime_type="application/json"
    )
    response = model.generate_content([prompt, sanitized], generation_config=config)
    try:
        return json.loads(response.text)
    except Exception:
        return {"error": "JSON parse failed", "fhir_bundle": None}


def run_full_system(model, report_text, age=DEFAULT_AGE, gender=DEFAULT_GENDER):
    from utils.agent import run_agent

    extracted_data = {"type": "text", "content": report_text}
    return run_agent(age, gender, DEFAULT_LANGUAGE, extracted_data, model, skip_routing=True)


VARIANTS = [
    ("B0 - Naive (No Knowledge, No Schema)", run_naive),
    ("B1 - No Knowledge Base", run_no_rag),
    ("B2 - No PII Guard", run_no_pii),
    ("B3 - No Agent Routing", run_no_agent),
    ("B4 - Full System (Ours)", run_full_system),
]


def score_result(gt_report, result):
    if "error" in result:
        return 0.0, 0.0, 0.0, 0.0

    ai_str = json.dumps(result)
    eval_res = evaluate_case(gt_report, ai_str)
    hal = eval_res.get("hallucination_score", 0.0)

    text_parts = [
        str(result.get("health_status_reason", "")),
        str(result.get("scariest_word_translated", "")),
        str(result.get("age_specific_context", "")),
    ]
    if isinstance(result.get("foods_to_eat"), list):
        text_parts += result["foods_to_eat"]
    if isinstance(result.get("foods_to_avoid"), list):
        text_parts += result["foods_to_avoid"]
    if len(text_parts) < 3:
        text_parts = [ai_str]

    readability = calculate_readability(" ".join(text_parts))
    fhir_score, _ = validate_fhir_bundle(result.get("fhir_bundle"))
    return (
        hal,
        readability["flesch_kincaid_grade"],
        readability["flesch_reading_ease"],
        fhir_score,
    )


def run_ablation(input_file=REAL_WORLD_CASES_CSV, count=DEFAULT_ABLATION_COUNT, output_file=ABLATION_RESULTS_JSON):
    api_key = get_api_key()
    if not api_key:
        return None

    genai.configure(api_key=api_key)
    cases = load_cases(input_file, count)
    if not cases:
        print(f"ERROR: No cases in {input_file}. Run: python download_pmc.py")
        return None

    print(f"Ablation study | input={input_file} | n={len(cases)}\n")
    base_model = genai.GenerativeModel(EVAL_MODEL)
    all_results = {}

    for variant_name, runner in VARIANTS:
        print("=" * 60)
        print(f"Running: {variant_name}")
        print("=" * 60)

        hal_list, grade_list, ease_list, fhir_list = [], [], [], []
        successful = 0

        for idx, case in enumerate(cases):
            gt = case.get("ground_truth_report", "")
            if not gt.strip():
                continue
            print(f"  Case {idx + 1}/{len(cases)}...", end=" ", flush=True)

            try:
                if variant_name.startswith("B0"):
                    result = runner(base_model, gt)
                else:
                    result = runner(base_model, gt)

                hal, grade, ease, fhir = score_result(gt, result)
                hal_list.append(hal)
                grade_list.append(grade)
                ease_list.append(ease)
                fhir_list.append(fhir)
                successful += 1
                print(f"OK (faith={hal:.1f}, FK={grade:.1f}, FHIR={fhir*100:.0f}%)")
            except Exception as e:
                print(f"ERROR: {e}")

        all_results[variant_name] = {
            "avg_hallucination": round(summarize(hal_list)["mean"], 2),
            "std_hallucination": round(summarize(hal_list)["std"], 2),
            "avg_grade_level": round(summarize(grade_list)["mean"], 2),
            "std_grade_level": round(summarize(grade_list)["std"], 2),
            "avg_readability_ease": round(summarize(ease_list)["mean"], 2),
            "std_readability_ease": round(summarize(ease_list)["std"], 2),
            "avg_fhir_validation": round(summarize(fhir_list)["mean"], 2),
            "std_fhir_validation": round(summarize(fhir_list)["std"], 2),
            "formatted_faithfulness": format_mean_std(hal_list),
            "formatted_fk_grade": format_mean_std(grade_list),
            "successful_runs": successful,
            "total_cases": len(cases),
            "is_literature": False,
        }

        print(
            f"\n  SUMMARY: Faithfulness {all_results[variant_name]['formatted_faithfulness']} | "
            f"FK {all_results[variant_name]['formatted_fk_grade']}\n"
        )

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)

    print("=" * 60)
    print(f"Ablation results saved to: {output_file}")
    print(f"Literature reference baselines (not experimental): {LITERATURE_BASELINES_PATH}")
    print("=" * 60)
    return all_results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run ablation study on evaluation dataset.")
    parser.add_argument("--input", default=REAL_WORLD_CASES_CSV)
    parser.add_argument("--count", type=int, default=DEFAULT_ABLATION_COUNT)
    parser.add_argument("--output", default=ABLATION_RESULTS_JSON)
    args = parser.parse_args()
    run_ablation(args.input, args.count, args.output)
