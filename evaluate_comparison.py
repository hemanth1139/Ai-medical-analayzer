import os
import csv
import json
import warnings

# Suppress the FutureWarning from the deprecated google.generativeai package
warnings.filterwarnings("ignore", category=FutureWarning)

import google.generativeai as genai
from dotenv import load_dotenv

# Import metrics and core agent runner
from utils.agent import run_agent
from evaluation.metrics import calculate_readability, validate_fhir_bundle
from evaluate_hallucination import evaluate_case

load_dotenv()

def get_configured_api_key():
    """Load and validate the GEMINI_API_KEY from the environment."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or api_key == "PASTE_YOUR_KEY_HERE":
        print("=" * 60)
        print("ERROR: GEMINI_API_KEY not found or not set!")
        print("Please open the .env file in the project root and add:")
        print("  GEMINI_API_KEY=your_actual_key_here")
        print("Get a free key from: https://aistudio.google.com")
        print("=" * 60)
        return None
    return api_key


def run_comparison_benchmark(input_file="real_world_cases.csv", count=5):
    api_key = get_configured_api_key()
    if not api_key:
        return

    # Configure genai ONCE at the start — this is shared by all modules
    genai.configure(api_key=api_key)

    print(f"Loading first {count} test cases from {input_file}...")

    cases = []
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                cases.append(row)
                if len(cases) >= count:
                    break
    except FileNotFoundError:
        print(f"Error: {input_file} not found. Run download_pmc.py first.")
        return

    if not cases:
        print("Error: No cases found in the dataset file.")
        return

    print(f"Loaded {len(cases)} cases. Starting benchmark...")

    # Configuration definitions to benchmark
    configs = [
        {"name": "Deterministic (Temp 0.0)", "temp": 0.0},
        {"name": "Exploratory (Temp 0.7)", "temp": 0.7}
    ]

    results = {}

    for config in configs:
        name = config["name"]
        temp = config["temp"]
        print(f"\nBenchmarking configuration: {name} (Temperature: {temp})...")

        # Build a model instance for this temperature configuration
        gen_config = genai.types.GenerationConfig(
            temperature=temp,
            response_mime_type="application/json"
        )
        model = genai.GenerativeModel('gemini-2.5-flash', generation_config=gen_config)

        total_hallucination_score = 0.0
        total_readability_grade = 0.0
        total_readability_ease = 0.0
        total_fhir_score = 0.0
        successful_runs = 0

        for idx, case in enumerate(cases):
            print(f"  Running case {idx+1}/{len(cases)}...", end=" ", flush=True)
            gt_report = case.get("ground_truth_report", "")

            if not gt_report.strip():
                print("SKIPPED (empty report)")
                continue

            # Form payload matching app.py expectations
            extracted_data = {"type": "text", "content": gt_report}

            try:
                # Run the medical advice agent
                raw_result = run_agent("45", "Male", "English", extracted_data, model)

                # Check for errors in agent output
                if "error" in raw_result:
                    print(f"AGENT ERROR: {raw_result['error'][:80]}...")
                    continue

                print("OK")

                # Evaluate hallucination using LLM-as-a-judge
                ai_advice_str = json.dumps(raw_result)
                eval_res = evaluate_case(gt_report, ai_advice_str)

                # Calculate Readability on the plain-text portions of the response
                text_parts = [
                    str(raw_result.get("health_status_reason", "")),
                    str(raw_result.get("scariest_word_translated", "")),
                    str(raw_result.get("age_specific_context", "")),
                ]
                if isinstance(raw_result.get("foods_to_eat"), list):
                    text_parts += raw_result["foods_to_eat"]
                if isinstance(raw_result.get("foods_to_avoid"), list):
                    text_parts += raw_result["foods_to_avoid"]

                combined_text = " ".join(text_parts)
                readability = calculate_readability(combined_text)

                # Validate FHIR bundle compliance
                fhir_bundle = raw_result.get("fhir_bundle")
                fhir_score, _ = validate_fhir_bundle(fhir_bundle)

                total_hallucination_score += eval_res.get("hallucination_score", 0.0)
                total_readability_grade += readability["flesch_kincaid_grade"]
                total_readability_ease += readability["flesch_reading_ease"]
                total_fhir_score += fhir_score
                successful_runs += 1

            except Exception as e:
                print(f"EXCEPTION: {e}")

        # Calculate averages for this configuration
        if successful_runs > 0:
            avg_hal = total_hallucination_score / successful_runs
            avg_grade = total_readability_grade / successful_runs
            avg_ease = total_readability_ease / successful_runs
            avg_fhir = total_fhir_score / successful_runs
        else:
            avg_hal, avg_grade, avg_ease, avg_fhir = 0.0, 0.0, 0.0, 0.0

        print(f"\n  [{name}] Results ({successful_runs}/{len(cases)} successful):")
        print(f"    Hallucination (Faithfulness): {avg_hal:.2f} / 10.0")
        print(f"    Flesch-Kincaid Grade Level:   {avg_grade:.2f}  (lower = simpler)")
        print(f"    Flesch Reading Ease:          {avg_ease:.2f}  (higher = easier)")
        print(f"    FHIR Bundle Compliance:       {avg_fhir * 100:.1f}%")

        results[name] = {
            "avg_hallucination": avg_hal,
            "avg_grade_level": avg_grade,
            "avg_readability_ease": avg_ease,
            "avg_fhir_validation": avg_fhir,
            "successful_runs": successful_runs,
            "total_cases": len(cases)
        }

    # Generate Markdown report table (IEEE paper ready)
    report_md = "# Model Configuration Benchmarking Report\n\n"
    report_md += "> Evaluated on PMC-Patients real-world clinical case summaries (N={})\n\n".format(count)
    report_md += "| Configuration | Hallucination Score (Faithfulness 0-10) | FK Grade Level (Lower=Simpler) | Flesch Reading Ease (Higher=Easier) | FHIR Bundle Compliance | Successful Cases |\n"
    report_md += "| --- | --- | --- | --- | --- | --- |\n"

    for name, m in results.items():
        report_md += (
            f"| {name} "
            f"| {m['avg_hallucination']:.2f} / 10.0 "
            f"| {m['avg_grade_level']:.2f} "
            f"| {m['avg_readability_ease']:.2f} "
            f"| {m['avg_fhir_validation'] * 100:.1f}% "
            f"| {m['successful_runs']} / {m['total_cases']} |\n"
        )

    report_md += "\n## Metric Definitions\n"
    report_md += "- **Hallucination Score**: LLM-as-a-Judge (Gemini 2.5 Flash) evaluating faithfulness of AI advice against the source clinical report. 10.0 = perfectly faithful, 0.0 = completely hallucinated.\n"
    report_md += "- **FK Grade Level**: Flesch-Kincaid Grade Level of the generated patient advice text. Grade 5-7 is the target for patient-facing health communication.\n"
    report_md += "- **Flesch Reading Ease**: Score 0-100. 60-70 = 'Standard' (understandable by 13-15 year olds). Higher is better for patient-facing content.\n"
    report_md += "- **FHIR Bundle Compliance**: Percentage of required FHIR R4 Observation fields (resourceType, type, status, code) present and correct.\n"

    print("\n" + "=" * 60)
    print("COMPARATIVE EVALUATION COMPLETE")
    print("=" * 60)
    print(report_md)

    with open("comparison_results.md", "w", encoding="utf-8") as f:
        f.write(report_md)
    print("Results saved to: comparison_results.md")


if __name__ == "__main__":
    run_comparison_benchmark()
