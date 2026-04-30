import os
import json
import csv
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# We will use Gemini as the LLM Judge since it's already integrated in the project.
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("WARNING: GEMINI_API_KEY not found in environment variables. Please check your .env file.")
else:
    genai.configure(api_key=api_key)

# Initialize judge model (using Gemini 2.5 Flash for fast/cheap eval, but can be switched to Pro)
judge_model = genai.GenerativeModel('gemini-2.5-flash')

def evaluate_case(ground_truth_report: str, ai_generated_advice: str) -> dict:
    """
    Takes the original medical report and the AI's generated advice and evaluates
    for hallucinations or invented facts using LLM-as-a-Judge.
    """
    prompt = f"""
Compare the AI advice to the raw medical report. Did the AI invent any medical conditions, metrics, or statistics not present in the original report? Output ONLY a JSON object with two keys: 'hallucination_score' (0.0 to 10.0, where 10.0 means ZERO hallucinations/perfectly faithful) and 'reasoning' (a 1-sentence explanation).

Raw Medical Report:
{ground_truth_report}

AI Generated Advice:
{ai_generated_advice}
    """
    
    config = genai.types.GenerationConfig(response_mime_type="application/json")
    
    try:
        response = judge_model.generate_content(prompt, generation_config=config)
        result = json.loads(response.text)
        
        # Fallback if the judge returns malformed keys
        if 'hallucination_score' not in result:
             result['hallucination_score'] = 0.0
             result['reasoning'] = "Failed to extract score from Judge API."
             
        # Cast score to float for calculations
        result['hallucination_score'] = float(result['hallucination_score'])
        return result
    except Exception as e:
        print(f"Error calling judge API: {e}")
        return {
            "hallucination_score": 0.0,
            "reasoning": f"Error during evaluation: {str(e)}"
        }

def read_data(input_file: str):
    """Reads cases from either a CSV or JSONL file."""
    data = []
    if input_file.endswith('.csv'):
        with open(input_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append(row)
    elif input_file.endswith('.jsonl'):
        with open(input_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    data.append(json.loads(line))
    else:
        raise ValueError("Unsupported file format. Use .csv or .jsonl")
    return data

def run_evaluation_suite(input_file: str, output_file: str):
    """
    Batch processing loop to run the evaluation across all test cases
    and aggregate the final hallucination scores.
    """
    print(f"Starting evaluation suite using input file: {input_file}")
    
    try:
        data = read_data(input_file)
    except FileNotFoundError:
        print(f"Input file '{input_file}' not found. Creating a dummy dataset to demonstrate functionality...")
        data = [
            {
                "ground_truth_report": "Hemoglobin: 14 g/dL. Patient is healthy. No other abnormalities.",
                "ai_generated_advice": '{"health_status": "Good", "foods_to_eat": ["Spinach", "Moong Dal"], "doctor_visit_needed": false}'
            },
            {
                "ground_truth_report": "Blood pressure is 120/80. Normal ECG. No signs of heart attack.",
                "ai_generated_advice": '{"health_status": "Critical", "health_status_reason": "Patient is having a severe heart attack and requires immediate surgery.", "doctor_visit_needed": true}'
            }
        ]
        # create dummy file for the user to see the format
        with open(input_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["ground_truth_report", "ai_generated_advice"])
            writer.writeheader()
            writer.writerows(data)
            
    if not data:
        print("Dataset is empty. Exiting.")
        return

    # Validate column presence
    if 'ground_truth_report' not in data[0] or 'ai_generated_advice' not in data[0]:
        raise ValueError("Input file must contain 'ground_truth_report' and 'ai_generated_advice' columns/keys.")

    results = []
    total_score = 0.0
    
    for index, row in enumerate(data):
        print(f"Evaluating case {index + 1}/{len(data)}...")
        
        gt_report = str(row['ground_truth_report'])
        ai_advice = str(row['ai_generated_advice'])
        
        eval_result = evaluate_case(gt_report, ai_advice)
        
        total_score += eval_result['hallucination_score']
        
        # Store results for CSV export
        row_dict = dict(row)
        row_dict['hallucination_score'] = eval_result['hallucination_score']
        row_dict['reasoning'] = eval_result['reasoning']
        results.append(row_dict)
        
    avg_score = total_score / len(data) if data else 0.0
    
    # Save the aggregated results to CSV
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        fieldnames = list(results[0].keys())
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    
    print("\n" + "="*50)
    print(f"Evaluation Complete! Processed {len(data)} test cases.")
    print(f"Average Hallucination Score (Faithfulness): {avg_score:.2f} / 10.0")
    print(f"Detailed results saved to: {output_file}")
    print("="*50 + "\n")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Evaluate medical AI hallucinations.")
    parser.add_argument("--input", type=str, default="evaluation_cases.csv", help="Path to input CSV or JSONL file containing 50+ test cases.")
    parser.add_argument("--output", type=str, default="evaluation_results.csv", help="Path to aggregated output CSV file.")
    
    args = parser.parse_args()
    run_evaluation_suite(args.input, args.output)
