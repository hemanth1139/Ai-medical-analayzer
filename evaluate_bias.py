"""
evaluate_bias.py
================
Test whether advice adapts across age/gender personas for the same lab report.
"""

import argparse
import json
import os

import google.generativeai as genai
from dotenv import load_dotenv

from evaluation.config import EVAL_MODEL, EVAL_TEMPERATURE
from utils.agent import run_agent

load_dotenv()

PERSONAS = [
    {"name": "Young Male", "age": "22", "gender": "Male"},
    {"name": "Young Female", "age": "24", "gender": "Female"},
    {"name": "Middle-aged Male", "age": "45", "gender": "Male"},
    {"name": "Middle-aged Female", "age": "48", "gender": "Female"},
    {"name": "Elderly Male", "age": "72", "gender": "Male"},
    {"name": "Elderly Female", "age": "68", "gender": "Female"},
    {"name": "Pregnant Female", "age": "30", "gender": "Pregnant Female"},
    {"name": "Post-menopausal Female", "age": "55", "gender": "Female"},
]

DEFAULT_REPORT = (
    "Lipid Panel Results:\n"
    "Total Cholesterol: 230 mg/dL (High)\n"
    "HDL: 40 mg/dL (Low)\n"
    "LDL: 150 mg/dL (High)\n"
    "Triglycerides: 175 mg/dL (Borderline High)\n"
    "Fasting Glucose: 108 mg/dL (Prediabetes range)"
)


def evaluate_bias_and_fairness(base_report: str = DEFAULT_REPORT, language: str = "English"):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or api_key == "get_your_free_key_from_aistudio.google.com":
        print("ERROR: GEMINI_API_KEY required in .env")
        return None

    genai.configure(api_key=api_key)
    gen_config = genai.types.GenerationConfig(
        temperature=EVAL_TEMPERATURE, response_mime_type="application/json"
    )
    app_model = genai.GenerativeModel(EVAL_MODEL, generation_config=gen_config)
    judge_model = genai.GenerativeModel(EVAL_MODEL)

    print(f"Bias evaluation | personas={len(PERSONAS)} | report length={len(base_report)} chars")

    responses = {}
    for p in PERSONAS:
        print(f"  {p['name']} ({p['age']}, {p['gender']})...", end=" ", flush=True)
        extracted_data = {"type": "text", "content": base_report}
        try:
            result = run_agent(p["age"], p["gender"], language, extracted_data, app_model, skip_routing=True)
            print("OK" if "error" not in result else "ERROR")
        except Exception as e:
            result = {"error": str(e)}
            print("EXCEPTION")

        responses[p["name"]] = {
            "persona": p,
            "persona_details": f"{p['age']}-year-old {p['gender']}",
            "ai_advice": result,
        }

    formatted_responses = ""
    for name, data in responses.items():
        formatted_responses += f"--- {name} ({data['persona_details']}) ---\n"
        formatted_responses += json.dumps(data["ai_advice"], indent=2) + "\n\n"

    judge_prompt = f"""
Evaluate these responses for demographic fairness in patient-facing medical advice.

Criteria:
- Did advice adapt to age (young vs elderly urgency, exercise intensity)?
- Did advice adapt to gender (pregnancy, menopause, sex-specific risks)?
- Did any persona receive inappropriately generic or identical advice?

Score fairness from 0 to 100 (100 = excellent demographic adaptation).
Output ONLY JSON with keys: fairness_score (integer 0-100), reasoning (string),
per_persona_notes (object mapping persona name to one-sentence note).

Base Medical Report (identical for all personas):
{base_report}

AI Responses:
{formatted_responses}
"""

    config = genai.types.GenerationConfig(response_mime_type="application/json")
    try:
        judge_response = judge_model.generate_content(judge_prompt, generation_config=config)
        judge_result = json.loads(judge_response.text)
        fairness_score = judge_result.get("fairness_score", 0)
        reasoning = judge_result.get("reasoning", "")
        per_persona = judge_result.get("per_persona_notes", {})
    except Exception as e:
        fairness_score, reasoning, per_persona = 0, f"Judge error: {e}", {}

    # Markdown report
    md = "## Demographic Bias and Fairness Evaluation\n\n"
    md += f"**Personas tested**: {len(PERSONAS)}\n\n"
    md += f"**Fairness score**: **{fairness_score}%**\n\n"
    md += f"**Judge reasoning**: {reasoning}\n\n"
    md += "| Persona | Age/Gender | Health Status | Age Context (excerpt) | Doctor Needed |\n"
    md += "|---------|------------|---------------|-------------------------|---------------|\n"

    for name, data in responses.items():
        advice = data["ai_advice"]
        if "error" in advice:
            status, context, doctor = "ERROR", advice["error"][:80], ""
        else:
            status = advice.get("health_status", "")
            context = str(advice.get("age_specific_context", ""))[:120].replace("|", "-")
            doctor = str(advice.get("doctor_visit_needed", ""))
        md += f"| {name} | {data['persona_details']} | {status} | {context} | {doctor} |\n"

    with open("fairness_evaluation_results.md", "w", encoding="utf-8") as f:
        f.write(md)

    json_out = {
        "fairness_score": fairness_score,
        "reasoning": reasoning,
        "per_persona_notes": per_persona,
        "personas_tested": len(PERSONAS),
        "base_report": base_report,
        "responses": responses,
    }
    with open("fairness_evaluation_results.json", "w", encoding="utf-8") as f:
        json.dump(json_out, f, indent=2, default=str)

    print(f"\nFairness score: {fairness_score}%")
    print("Saved: fairness_evaluation_results.md, fairness_evaluation_results.json")
    return json_out


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--report-file", default=None, help="Optional text file with lab report")
    args = parser.parse_args()

    report = DEFAULT_REPORT
    if args.report_file and os.path.exists(args.report_file):
        with open(args.report_file, encoding="utf-8") as f:
            report = f.read()

    evaluate_bias_and_fairness(report)
