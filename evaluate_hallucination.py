import os
import json
import csv
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

import google.generativeai as genai
from dotenv import load_dotenv

# ─── Optional judge clients (degrade gracefully if key is missing) ───────────
try:
    from groq import Groq
    _groq_available = True
except ImportError:
    _groq_available = False

try:
    from openai import OpenAI as OpenRouterClient
    _openrouter_available = True
except ImportError:
    _openrouter_available = False

from evaluation.metrics import calculate_readability, validate_fhir_bundle

# Load environment variables
load_dotenv()

# ─── Judge configuration ──────────────────────────────────────────────────────
GEMINI_KEY       = os.environ.get("GEMINI_API_KEY", "")
GROQ_KEY         = os.environ.get("GROQ_API_KEY", "")
OPENROUTER_KEY   = os.environ.get("OPENROUTER_API_KEY", "")

# Gemini judge setup
_gemini_judge = None
if GEMINI_KEY and GEMINI_KEY != "PASTE_YOUR_KEY_HERE":
    genai.configure(api_key=GEMINI_KEY)
    _gemini_judge = genai.GenerativeModel("gemini-2.5-flash")
    print("[Judge] Gemini 2.5 Flash  ✓ ready")
else:
    print("[Judge] Gemini 2.5 Flash  ✗ skipped (no key)")

# Groq judge setup (Llama 3.3 70B — free, very fast)
_groq_judge = None
if _groq_available and GROQ_KEY and GROQ_KEY != "PASTE_YOUR_GROQ_KEY_HERE":
    _groq_judge = Groq(api_key=GROQ_KEY)
    print("[Judge] Groq Llama 3.3 70B  ✓ ready")
else:
    print("[Judge] Groq Llama 3.3 70B  ✗ skipped (no key or package)")

# OpenRouter judge setup (Mistral 7B free tier)
_openrouter_judge = None
if _openrouter_available and OPENROUTER_KEY and OPENROUTER_KEY != "PASTE_YOUR_OPENROUTER_KEY_HERE":
    _openrouter_judge = OpenRouterClient(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_KEY,
    )
    print("[Judge] OpenRouter Mistral 7B  ✓ ready")
else:
    print("[Judge] OpenRouter Mistral 7B  ✗ skipped (no key or package)")

# Ensure at least one judge is active
_active_judges = sum([
    _gemini_judge is not None,
    _groq_judge is not None,
    _openrouter_judge is not None,
])
if _active_judges == 0:
    print("WARNING: No LLM judges configured! Add at least one API key to your .env file.")


# ─── Shared judge prompt builder ──────────────────────────────────────────────
def _build_prompt(ground_truth_report: str, ai_generated_advice: str) -> str:
    return f"""You are a medical AI auditor. Compare the AI-generated advice to the raw medical report below.

Did the AI invent any medical conditions, metrics, or statistics NOT present in the original report?

Output ONLY a valid JSON object with exactly two keys:
- "hallucination_score": a float from 0.0 to 10.0 (10.0 = ZERO hallucinations / perfectly faithful, 0.0 = completely fabricated)
- "reasoning": a single sentence explaining your score

Raw Medical Report:
{ground_truth_report}

AI Generated Advice:
{ai_generated_advice}"""


def _parse_score(raw: str, judge_name: str) -> dict:
    """Parse a JSON score string, with graceful fallback."""
    try:
        result = json.loads(raw)
        score = float(result.get("hallucination_score", 0.0))
        # Clamp to [0, 10]
        score = max(0.0, min(10.0, score))
        return {"hallucination_score": score, "reasoning": result.get("reasoning", ""), "judge": judge_name}
    except Exception as e:
        return {"hallucination_score": 0.0, "reasoning": f"Parse error from {judge_name}: {e}", "judge": judge_name}


# ─── Individual judge callers ─────────────────────────────────────────────────
def _call_gemini(prompt: str) -> dict:
    try:
        config = genai.types.GenerationConfig(response_mime_type="application/json")
        response = _gemini_judge.generate_content(prompt, generation_config=config)
        return _parse_score(response.text, "Gemini 2.5 Flash")
    except Exception as e:
        return {"hallucination_score": 0.0, "reasoning": f"Gemini error: {e}", "judge": "Gemini 2.5 Flash"}


def _call_groq(prompt: str) -> dict:
    try:
        chat = _groq_judge.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a medical AI auditor. Respond ONLY with a valid JSON object."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        return _parse_score(chat.choices[0].message.content, "Groq Llama 3.3 70B")
    except Exception as e:
        return {"hallucination_score": 0.0, "reasoning": f"Groq error: {e}", "judge": "Groq Llama 3.3 70B"}


def _call_openrouter(prompt: str) -> dict:
    try:
        chat = _openrouter_judge.chat.completions.create(
            model="mistralai/mistral-7b-instruct:free",
            messages=[
                {"role": "system", "content": "You are a medical AI auditor. Respond ONLY with a valid JSON object."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
        )
        return _parse_score(chat.choices[0].message.content, "OpenRouter Mistral 7B")
    except Exception as e:
        return {"hallucination_score": 0.0, "reasoning": f"OpenRouter error: {e}", "judge": "OpenRouter Mistral 7B"}


# ─── Public API ───────────────────────────────────────────────────────────────
def evaluate_case(ground_truth_report: str, ai_generated_advice: str) -> dict:
    """
    Ensemble LLM-as-a-Judge evaluation.

    Runs up to 3 independent judges (Gemini 2.5 Flash, Groq Llama 3.3 70B,
    OpenRouter Mistral 7B) and averages their hallucination scores.

    Returns a dict with:
      - hallucination_score  : float 0–10 (ensemble average)
      - reasoning            : combined reasoning from all active judges
      - judge_breakdown      : list of per-judge results
    """
    prompt = _build_prompt(ground_truth_report, ai_generated_advice)
    judge_results = []

    if _gemini_judge:
        judge_results.append(_call_gemini(prompt))

    if _groq_judge:
        judge_results.append(_call_groq(prompt))

    if _openrouter_judge:
        judge_results.append(_call_openrouter(prompt))

    if not judge_results:
        return {
            "hallucination_score": 0.0,
            "reasoning": "No judges configured — check API keys in .env",
            "judge_breakdown": [],
        }

    avg_score = sum(r["hallucination_score"] for r in judge_results) / len(judge_results)
    combined_reasoning = " | ".join(
        f"[{r['judge']}]: {r['reasoning']}" for r in judge_results
    )

    return {
        "hallucination_score": round(avg_score, 2),
        "reasoning": combined_reasoning,
        "judge_breakdown": judge_results,
    }


# ─── I/O helpers ─────────────────────────────────────────────────────────────
def read_data(input_file: str):
    """Reads cases from either a CSV or JSONL file."""
    data = []
    if input_file.endswith(".csv"):
        with open(input_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append(row)
    elif input_file.endswith(".jsonl"):
        with open(input_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    data.append(json.loads(line))
    else:
        raise ValueError("Unsupported file format. Use .csv or .jsonl")
    return data


def run_evaluation_suite(input_file: str, output_file: str):
    """
    Batch processing loop — runs the ensemble judge across all test cases
    and aggregates the final hallucination scores into a CSV.
    """
    print(f"\nStarting evaluation suite | input: {input_file}")
    print(f"Active judges: {_active_judges} / 3  (Gemini + Groq + OpenRouter)\n")

    try:
        data = read_data(input_file)
    except FileNotFoundError:
        print(f"Input file '{input_file}' not found. Creating a dummy dataset...")
        data = [
            {
                "ground_truth_report": "Hemoglobin: 14 g/dL. Patient is healthy. No other abnormalities.",
                "ai_generated_advice": '{"health_status": "Good", "foods_to_eat": ["Spinach", "Moong Dal"], "doctor_visit_needed": false}',
            },
            {
                "ground_truth_report": "Blood pressure is 120/80. Normal ECG. No signs of heart attack.",
                "ai_generated_advice": '{"health_status": "Critical", "health_status_reason": "Patient is having a severe heart attack and requires immediate surgery.", "doctor_visit_needed": true}',
            },
        ]
        with open(input_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["ground_truth_report", "ai_generated_advice"])
            writer.writeheader()
            writer.writerows(data)

    if not data:
        print("Dataset is empty. Exiting.")
        return

    if "ground_truth_report" not in data[0] or "ai_generated_advice" not in data[0]:
        raise ValueError("Input file must contain 'ground_truth_report' and 'ai_generated_advice' columns/keys.")

    results = []
    total_score = 0.0

    for index, row in enumerate(data):
        print(f"Evaluating case {index + 1}/{len(data)}...", end=" ", flush=True)

        gt_report = str(row["ground_truth_report"])
        ai_advice = str(row["ai_generated_advice"])

        eval_result = evaluate_case(gt_report, ai_advice)
        total_score += eval_result["hallucination_score"]
        print(f"score={eval_result['hallucination_score']:.1f}")

        # Calculate readability & validate FHIR schema
        readability_ease = 0.0
        readability_grade = 0.0
        fhir_score = 1.0

        try:
            advice_dict = json.loads(ai_advice)
            combined_text = " ".join([
                str(advice_dict.get("health_status_reason", "")),
                " ".join(advice_dict.get("foods_to_eat", []) if isinstance(advice_dict.get("foods_to_eat"), list) else []),
                " ".join(advice_dict.get("foods_to_avoid", []) if isinstance(advice_dict.get("foods_to_avoid"), list) else []),
                str(advice_dict.get("scariest_word_translated", "")),
                str(advice_dict.get("age_specific_context", "")),
            ])
            readability_scores = calculate_readability(combined_text)
            readability_ease = readability_scores["flesch_reading_ease"]
            readability_grade = readability_scores["flesch_kincaid_grade"]
            fhir_bundle = advice_dict.get("fhir_bundle")
            fhir_score, _ = validate_fhir_bundle(fhir_bundle)
        except Exception:
            readability_scores = calculate_readability(ai_advice)
            readability_ease = readability_scores["flesch_reading_ease"]
            readability_grade = readability_scores["flesch_kincaid_grade"]
            fhir_score = 0.0

        row_dict = dict(row)
        row_dict["hallucination_score"]     = eval_result["hallucination_score"]
        row_dict["reasoning"]               = eval_result["reasoning"]
        row_dict["judge_breakdown"]         = json.dumps(eval_result["judge_breakdown"])
        row_dict["flesch_reading_ease"]     = readability_ease
        row_dict["flesch_kincaid_grade"]    = readability_grade
        row_dict["fhir_validation_score"]   = fhir_score
        # Placeholders for Clinician Audit (IEEE Reviewer expectation)
        row_dict["clinician_grade_1_to_10"] = ""
        row_dict["is_clinically_safe"]      = ""
        row_dict["clinician_feedback_notes"] = ""
        results.append(row_dict)

    avg_score = total_score / len(data) if data else 0.0

    with open(output_file, "w", encoding="utf-8", newline="") as f:
        fieldnames = list(results[0].keys())
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print("\n" + "=" * 60)
    print(f"Evaluation Complete! Processed {len(data)} test cases.")
    print(f"Judges used: {_active_judges} / 3  (ensemble average)")
    print(f"Average Hallucination Score (Faithfulness): {avg_score:.2f} / 10.0")
    print(f"Detailed results saved to: {output_file}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Evaluate medical AI hallucinations using an ensemble of LLM judges.")
    parser.add_argument("--input",  type=str, default="evaluation_cases.csv",  help="Path to input CSV or JSONL file.")
    parser.add_argument("--output", type=str, default="evaluation_results.csv", help="Path to output CSV file.")
    args = parser.parse_args()
    run_evaluation_suite(args.input, args.output)
