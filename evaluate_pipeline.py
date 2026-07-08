"""
evaluate_pipeline.py
====================
End-to-end evaluation: run the full Patient Action Guide agent on a dataset,
score outputs, and write a detailed results CSV plus summary JSON.

Usage:
  python evaluate_pipeline.py
  python evaluate_pipeline.py --input real_world_cases.csv --count 20
  python evaluate_pipeline.py --input evaluation_cases.csv --skip-agent  # score existing advice only
"""

import argparse
import csv
import json
import os
import sys
import warnings
from typing import List, Optional

warnings.filterwarnings("ignore", category=FutureWarning)

import google.generativeai as genai
from dotenv import load_dotenv

from evaluation.config import (
    DEFAULT_AGE,
    DEFAULT_GENDER,
    DEFAULT_LANGUAGE,
    EVAL_MODEL,
    EVAL_TEMPERATURE,
    EVAL_SUMMARY_JSON,
    PIPELINE_RESULTS_CSV,
    REAL_WORLD_CASES_CSV,
)
from evaluation.metrics import calculate_readability, validate_fhir_bundle
from evaluation.stats import format_mean_std, summarize
from evaluate_hallucination import evaluate_case
from utils.agent import run_agent

load_dotenv()


def get_api_key() -> Optional[str]:
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key or key in ("PASTE_YOUR_KEY_HERE", "get_your_free_key_from_aistudio.google.com"):
        return None
    return key


def load_cases(path: str, count: Optional[int]) -> List[dict]:
    cases = []
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cases.append(row)
            if count and len(cases) >= count:
                break
    return cases


def extract_advice_text(result: dict) -> str:
    if "error" in result:
        return ""
    parts = [
        str(result.get("health_status_reason", "")),
        str(result.get("scariest_word_translated", "")),
        str(result.get("age_specific_context", "")),
    ]
    for key in ("foods_to_eat", "foods_to_avoid", "daily_habits"):
        val = result.get(key)
        if isinstance(val, list):
            parts.extend(str(x) for x in val)
    return " ".join(p for p in parts if p)


def run_pipeline(
    input_file: str = REAL_WORLD_CASES_CSV,
    output_file: str = PIPELINE_RESULTS_CSV,
    summary_file: str = EVAL_SUMMARY_JSON,
    count: int = 20,
    skip_agent: bool = False,
    age: str = DEFAULT_AGE,
    gender: str = DEFAULT_GENDER,
    language: str = DEFAULT_LANGUAGE,
) -> dict:
    api_key = get_api_key()
    if not skip_agent and not api_key:
        print("ERROR: GEMINI_API_KEY required. Add it to .env or use --skip-agent.")
        sys.exit(1)

    if not os.path.exists(input_file):
        print(f"ERROR: {input_file} not found.")
        if input_file == REAL_WORLD_CASES_CSV:
            print("Run: python download_pmc.py --count 50")
        sys.exit(1)

    cases = load_cases(input_file, count)
    if not cases:
        print("ERROR: No cases in input file.")
        sys.exit(1)

    model = None
    if not skip_agent:
        genai.configure(api_key=api_key)
        gen_config = genai.types.GenerationConfig(
            temperature=EVAL_TEMPERATURE,
            response_mime_type="application/json",
        )
        model = genai.GenerativeModel(EVAL_MODEL, generation_config=gen_config)

    print(f"Pipeline evaluation | input={input_file} | n={len(cases)} | skip_agent={skip_agent}")

    results = []
    hal_scores, fk_grades, fk_ease, fhir_scores = [], [], [], []
    schema_valid_flags = []

    for idx, row in enumerate(cases):
        case_id = row.get("pmcid") or row.get("case_id") or f"case_{idx + 1}"
        gt_report = row.get("ground_truth_report", "").strip()
        print(f"  [{idx + 1}/{len(cases)}] {case_id}...", end=" ", flush=True)

        if not gt_report:
            print("SKIP (empty report)")
            continue

        ai_advice_raw = row.get("ai_generated_advice", "").strip()
        agent_result = None

        if not skip_agent:
            extracted = {"type": "text", "content": gt_report}
            try:
                agent_result = run_agent(age, gender, language, extracted, model)
            except Exception as e:
                agent_result = {"error": str(e)}

            if "error" in agent_result:
                print(f"AGENT ERROR")
                ai_advice_str = json.dumps(agent_result)
            else:
                ai_advice_str = json.dumps(agent_result)
                print("OK")
        else:
            if not ai_advice_raw:
                print("SKIP (no existing advice)")
                continue
            ai_advice_str = ai_advice_raw
            try:
                agent_result = json.loads(ai_advice_raw)
            except json.JSONDecodeError:
                agent_result = {"health_status_reason": ai_advice_raw}
            print("SCORE ONLY")

        # Hallucination / faithfulness (LLM-as-judge ensemble)
        eval_res = evaluate_case(gt_report, ai_advice_str)
        hal = eval_res.get("hallucination_score", 0.0)
        hal_scores.append(hal)

        # Readability
        if agent_result and "error" not in agent_result:
            combined = extract_advice_text(agent_result)
            readability = calculate_readability(combined)
            fhir_score, fhir_issues = validate_fhir_bundle(agent_result.get("fhir_bundle"))
            schema_valid = "error" not in agent_result
        else:
            readability = calculate_readability(ai_advice_str)
            fhir_score, fhir_issues = 0.0, ["agent error"]
            schema_valid = False

        fk_grades.append(readability["flesch_kincaid_grade"])
        fk_ease.append(readability["flesch_reading_ease"])
        fhir_scores.append(fhir_score)
        schema_valid_flags.append(schema_valid)

        out_row = dict(row)
        out_row["ai_generated_advice"] = ai_advice_str
        out_row["hallucination_score"] = hal
        out_row["reasoning"] = eval_res.get("reasoning", "")
        out_row["judge_breakdown"] = json.dumps(eval_res.get("judge_breakdown", []))
        out_row["flesch_reading_ease"] = readability["flesch_reading_ease"]
        out_row["flesch_kincaid_grade"] = readability["flesch_kincaid_grade"]
        out_row["fhir_validation_score"] = fhir_score
        out_row["fhir_issues"] = json.dumps(fhir_issues)
        out_row["schema_valid"] = schema_valid
        out_row["clinician_grade_1_to_10"] = row.get("clinician_grade_1_to_10", "")
        out_row["is_clinically_safe"] = row.get("is_clinically_safe", "")
        out_row["clinician_feedback_notes"] = row.get("clinician_feedback_notes", "")
        results.append(out_row)

    if not results:
        print("No results produced.")
        sys.exit(1)

    fieldnames = list(results[0].keys())
    with open(output_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    summary = {
        "input_file": input_file,
        "output_file": output_file,
        "cases_evaluated": len(results),
        "model": EVAL_MODEL,
        "temperature": EVAL_TEMPERATURE,
        "faithfulness": summarize(hal_scores, "hallucination_score"),
        "flesch_kincaid_grade": summarize(fk_grades, "flesch_kincaid_grade"),
        "flesch_reading_ease": summarize(fk_ease, "flesch_reading_ease"),
        "fhir_validation": summarize(fhir_scores, "fhir_validation_score"),
        "schema_valid_rate_pct": round(
            100.0 * sum(schema_valid_flags) / len(schema_valid_flags), 1
        ),
        "formatted": {
            "faithfulness": format_mean_std(hal_scores),
            "flesch_kincaid_grade": format_mean_std(fk_grades),
            "flesch_reading_ease": format_mean_std(fk_ease),
            "fhir_validation": format_mean_std(fhir_scores),
        },
    }

    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 60)
    print("PIPELINE EVALUATION COMPLETE")
    print("=" * 60)
    print(f"Cases evaluated     : {len(results)}")
    print(f"Faithfulness (0-10) : {summary['formatted']['faithfulness']}")
    print(f"FK Grade (lower=better): {summary['formatted']['flesch_kincaid_grade']}")
    print(f"Reading Ease        : {summary['formatted']['flesch_reading_ease']}")
    print(f"FHIR validation     : {summary['formatted']['fhir_validation']}")
    print(f"Schema valid rate   : {summary['schema_valid_rate_pct']}%")
    print(f"Results CSV         : {output_file}")
    print(f"Summary JSON        : {summary_file}")
    print("=" * 60)

    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="End-to-end pipeline evaluation.")
    parser.add_argument("--input", default=REAL_WORLD_CASES_CSV)
    parser.add_argument("--output", default=PIPELINE_RESULTS_CSV)
    parser.add_argument("--summary", default=EVAL_SUMMARY_JSON)
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--skip-agent", action="store_true")
    parser.add_argument("--age", default=DEFAULT_AGE)
    parser.add_argument("--gender", default=DEFAULT_GENDER)
    parser.add_argument("--language", default=DEFAULT_LANGUAGE)
    args = parser.parse_args()

    run_pipeline(
        input_file=args.input,
        output_file=args.output,
        summary_file=args.summary,
        count=args.count,
        skip_agent=args.skip_agent,
        age=args.age,
        gender=args.gender,
        language=args.language,
    )
