"""
clinician_review.py
===================
Export pipeline results for clinician rating, then import ratings back.

Usage:
  # Step 1: After evaluate_pipeline.py, create a review sheet for doctors
  python clinician_review.py export --input evaluation_results.csv

  # Step 2: Clinicians fill in clinician_grade_1_to_10, is_clinically_safe, clinician_feedback_notes

  # Step 3: Merge ratings back into results
  python clinician_review.py import --results evaluation_results.csv --ratings clinician_review_sheet.csv
"""

import argparse
import csv
import json
import sys
from typing import Optional


EXPORT_COLUMNS = [
    "case_id",
    "pmcid",
    "title",
    "ground_truth_report",
    "health_status",
    "health_status_reason",
    "doctor_visit_needed",
    "visit_urgency",
    "foods_to_eat_preview",
    "warning_signs_preview",
    "clinician_grade_1_to_10",
    "is_clinically_safe",
    "clinician_feedback_notes",
]

IMPORT_RATING_COLUMNS = [
    "clinician_grade_1_to_10",
    "is_clinically_safe",
    "clinician_feedback_notes",
]


def _preview_list(val, max_items: int = 2) -> str:
    if isinstance(val, list):
        return "; ".join(str(x) for x in val[:max_items])
    return str(val)[:200] if val else ""


def _case_id(row: dict, index: int) -> str:
    return row.get("case_id") or row.get("pmcid") or f"case_{index + 1}"


def export_review_sheet(input_file: str, output_file: str) -> int:
    rows_out = []
    with open(input_file, encoding="utf-8") as f:
        for idx, row in enumerate(csv.DictReader(f)):
            advice = {}
            raw = row.get("ai_generated_advice", "")
            if raw:
                try:
                    advice = json.loads(raw)
                except json.JSONDecodeError:
                    advice = {"health_status_reason": raw[:500]}

            rows_out.append(
                {
                    "case_id": _case_id(row, idx),
                    "pmcid": row.get("pmcid", ""),
                    "title": row.get("title", "")[:200],
                    "ground_truth_report": row.get("ground_truth_report", "")[:1500],
                    "health_status": advice.get("health_status", ""),
                    "health_status_reason": advice.get("health_status_reason", ""),
                    "doctor_visit_needed": advice.get("doctor_visit_needed", ""),
                    "visit_urgency": advice.get("visit_urgency", ""),
                    "foods_to_eat_preview": _preview_list(advice.get("foods_to_eat")),
                    "warning_signs_preview": _preview_list(advice.get("warning_signs")),
                    "clinician_grade_1_to_10": row.get("clinician_grade_1_to_10", ""),
                    "is_clinically_safe": row.get("is_clinically_safe", ""),
                    "clinician_feedback_notes": row.get("clinician_feedback_notes", ""),
                }
            )

    with open(output_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=EXPORT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows_out)

    print(f"Exported {len(rows_out)} cases to {output_file}")
    print("Clinicians should fill: clinician_grade_1_to_10 (1-10), is_clinically_safe (yes/no), clinician_feedback_notes")
    return len(rows_out)


def import_ratings(results_file: str, ratings_file: str, output_file: Optional[str] = None) -> dict:
    output_file = output_file or results_file

    ratings_by_id = {}
    with open(ratings_file, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cid = row.get("case_id", "").strip()
            if not cid:
                continue
            ratings_by_id[cid] = {
                col: row.get(col, "") for col in IMPORT_RATING_COLUMNS
            }

    updated = 0
    results = []
    with open(results_file, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        for col in IMPORT_RATING_COLUMNS:
            if col not in fieldnames:
                fieldnames.append(col)

        for idx, row in enumerate(reader):
            cid = _case_id(row, idx)
            if cid in ratings_by_id:
                for col, val in ratings_by_id[cid].items():
                    if val.strip():
                        row[col] = val
                        updated += 1
            results.append(row)

    with open(output_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    # Summarize clinician scores
    grades = []
    safe_yes = 0
    safe_total = 0
    for row in results:
        g = row.get("clinician_grade_1_to_10", "").strip()
        if g:
            try:
                grades.append(float(g))
            except ValueError:
                pass
        safe = row.get("is_clinically_safe", "").strip().lower()
        if safe in ("yes", "no", "true", "false"):
            safe_total += 1
            if safe in ("yes", "true"):
                safe_yes += 1

    summary = {
        "cases_with_ratings": len(grades),
        "mean_clinician_grade": round(sum(grades) / len(grades), 2) if grades else None,
        "clinical_safety_rate_pct": round(100.0 * safe_yes / safe_total, 1) if safe_total else None,
        "fields_updated": updated,
    }

    print(f"Imported ratings into {output_file}")
    print(f"  Cases with grades: {summary['cases_with_ratings']}")
    if summary["mean_clinician_grade"] is not None:
        print(f"  Mean clinician grade: {summary['mean_clinician_grade']}/10")
    if summary["clinical_safety_rate_pct"] is not None:
        print(f"  Marked clinically safe: {summary['clinical_safety_rate_pct']}%")

    return summary


def summarize_clinician_ratings(results_file: str) -> dict:
    grades, safe_flags = [], []
    with open(results_file, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            g = row.get("clinician_grade_1_to_10", "").strip()
            if g:
                try:
                    grades.append(float(g))
                except ValueError:
                    pass
            safe = row.get("is_clinically_safe", "").strip().lower()
            if safe in ("yes", "no", "true", "false"):
                safe_flags.append(safe in ("yes", "true"))

    from evaluation.stats import format_mean_std, summarize

    out = {
        "clinician_grade": summarize(grades, "clinician_grade"),
        "clinical_safety_rate_pct": round(100.0 * sum(safe_flags) / len(safe_flags), 1) if safe_flags else None,
        "formatted_grade": format_mean_std(grades),
    }
    print(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clinician review export/import.")
    sub = parser.add_subparsers(dest="command", required=True)

    exp = sub.add_parser("export", help="Create clinician review CSV from pipeline results")
    exp.add_argument("--input", default="evaluation_results.csv")
    exp.add_argument("--output", default="clinician_review_sheet.csv")

    imp = sub.add_parser("import", help="Merge clinician ratings back into results")
    imp.add_argument("--results", default="evaluation_results.csv")
    imp.add_argument("--ratings", default="clinician_review_sheet.csv")
    imp.add_argument("--output", default=None)

    summ = sub.add_parser("summarize", help="Print clinician rating summary")
    summ.add_argument("--input", default="evaluation_results.csv")

    args = parser.parse_args()

    if args.command == "export":
        export_review_sheet(args.input, args.output)
    elif args.command == "import":
        import_ratings(args.results, args.ratings, args.output)
    elif args.command == "summarize":
        summarize_clinician_ratings(args.input)
