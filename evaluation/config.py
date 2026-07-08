"""Shared configuration for evaluation scripts."""

import os

# Default sample sizes (override via CLI --count)
DEFAULT_ABLATION_COUNT = 10
DEFAULT_PIPELINE_COUNT = 20
DEFAULT_COMPARISON_COUNT = 10

# Default paths
REAL_WORLD_CASES_CSV = "real_world_cases.csv"
EVALUATION_CASES_CSV = "evaluation_cases.csv"
PIPELINE_RESULTS_CSV = "evaluation_results.csv"
ABLATION_RESULTS_JSON = "ablation_results.json"
CLINICIAN_REVIEW_CSV = "clinician_review_sheet.csv"
EVAL_SUMMARY_JSON = "evaluation_summary.json"

# Model settings for reproducibility
EVAL_MODEL = "gemini-2.5-flash"
EVAL_TEMPERATURE = 0.0

# Default patient persona for pipeline benchmarks
DEFAULT_AGE = "45"
DEFAULT_GENDER = "Male"
DEFAULT_LANGUAGE = "English"

LITERATURE_BASELINES_PATH = os.path.join(
    os.path.dirname(__file__), "literature_baselines.json"
)
