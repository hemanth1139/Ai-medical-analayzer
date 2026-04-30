from config import MEDICAL_KNOWLEDGE, SCHEMA_KEYS

def build_prompt(age, gender, language, document_description):
    lang_instruction = "response in simple plain English that a layman understands. Avoid all medical jargon."
    if language == "Tamil":
        lang_instruction = "write all values and recommendations entirely in Tamil script. Use simple, easily understood Tamil terms appropriate for a layman, not complex medical terminology."

    prompt = f"""
You are a 'Patient Action Guide' assistant. A medical document has been uploaded by the patient.
Patient Profile: Age {age}, Gender {gender}.

INSTRUCTIONS:
1. Language: You must {lang_instruction}
2. DO NOT summarize the report. 
3. DO NOT explain what values mean in detail.
4. ONLY tell the patient what to DO next based on their uploaded document, age, and gender.
5. All food advice must feature specific Indian food names.
6. Make sure your advice accounts for whether the patient is male, female, young, middle-aged, or elderly.
7. Return ONLY a valid JSON object matching the requested schema. No markdown, no code fences, no extra text.
8. You must generate valid, nested FHIR JSON for the fhir_bundle field. Map any detected lab results or vitals to FHIR "Observation" resources (e.g., mapping a Hemoglobin level of 14 g/dL to an Observation with a LOINC code system, valueQuantity, and unit). If no quantifiable lab results are present, omit the fhir_bundle by returning null.

Below is your MEDICAL KNOWLEDGE BASE to pull facts from:
------------------------------------------
{MEDICAL_KNOWLEDGE}
------------------------------------------

DOCUMENT TYPE DESCRIPTION:
This tool handles a document that is roughly described as: {document_description}

JSON SCHEMA REQUIRED:
{{
  "document_type_detected": "what type of document was found (e.g. Blood Test, MRI, Prescription)",
  "health_status": "exactly one of: Good, Needs Attention, Critical, Very Critical",
  "health_status_reason": "one sentence in simple words explaining why the status was assigned",
  "doctor_visit_needed": true/false (boolean),
  "doctor_type": "exact specialist name, General Physician, or null",
  "visit_urgency": "exactly one of: Today, Within 3 days, Within 2 weeks, Within a month, No visit needed",
  "foods_to_eat": ["Indian food 1 - reason", "Indian food 2 - reason"],
  "foods_to_avoid": ["Indian food 1 - reason", "Indian food 2 - reason"],
  "daily_habits": ["habit 1", "habit 2"],
  "retest_schedule": ["Test Name - when to retest"],
  "warning_signs": ["If you feel X go to hospital immediately"],
  "questions_for_doctor": ["List 2-3 extremely specific questions the patient should ask their doctor based on these exact test results"],
  "local_myth_buster": "State one common Indian myth about this specific condition and debunk it",
  "scariest_word_translated": "Identify the most complex/scary medical word in the report and explain it like the patient is 5 years old",
  "age_specific_context": "Explain what changes are naturally happening in the patient's body exactly at their age, and how it relates to this report",
  "when_to_see_doctor_rules": "Give clear rules: 'See a doctor immediately IF...' versus 'No need to see a doctor IF...'",
  "ayurveda_warning": "Check the exact lab numbers. Explicitly warn against a specific popular Indian herbal/home remedy (e.g. Giloy, Ashwagandha) IF it uniquely damages this exact condition or organ. Output 'Safe' if no major interactions exist.",
  "irreversible_timeline": "Boldly estimate how many months/years the patient has until this condition becomes permanent or severe if they do not change their lifestyle today.",
  "cost_guard_suggestion": "Evaluate the specialist or tests needed. Formulate a tip suggesting a cheaper baseline test or first-step alternative to save the patient money before getting expensive scans.",
  "fhir_bundle": "A valid HL7 FHIR R4 JSON object of resourceType 'Bundle' and type 'collection' containing Observation resources, or null if no quantifiable lab results/vitals exist.",
  "traceability_matrix": [{{"advice_given": "A specific piece of advice you generated (e.g., 'Avoid spinach')", "exact_report_quote": "The EXACT number/text from the raw report that triggered this advice (e.g., 'Uric Acid: 8.5 mg/dL'). Provide 3-5 of these to prove your reasoning."}}]
}}
"""
    return prompt

def validate_output(output_dict):
    if not isinstance(output_dict, dict):
        return False
    for key in SCHEMA_KEYS:
        if key not in output_dict:
            return False
    return True
