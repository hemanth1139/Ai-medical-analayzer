GEMINI_MODEL = "gemini-2.5-flash"
LANGUAGES = ["English", "Tamil"]

HEALTH_STATUS_LEVELS = {
    "Good": {"color": "#C8E6C9", "emoji": "✅"},
    "Needs Attention": {"color": "#FFF9C4", "emoji": "⚠️"},
    "Critical": {"color": "#FFE0B2", "emoji": "🚨"},
    "Very Critical": {"color": "#FFCCBC", "emoji": "🚑"},
}

SCHEMA_KEYS = [
    "document_type_detected",
    "health_status",
    "health_status_reason",
    "doctor_visit_needed",
    "doctor_type",
    "visit_urgency",
    "foods_to_eat",
    "foods_to_avoid",
    "daily_habits",
    "retest_schedule",
    "warning_signs",
    "questions_for_doctor",
    "local_myth_buster",
    "scariest_word_translated",
    "age_specific_context",
    "when_to_see_doctor_rules",
    "ayurveda_warning",
    "irreversible_timeline",
    "cost_guard_suggestion",
    "fhir_bundle",
    "traceability_matrix",
]

MEDICAL_KNOWLEDGE = """
Section 1 — Blood Sugar and Diabetes
Normal ranges for fasting glucose, post-meal glucose, HbA1c.
Fasting glucose should be below 100 mg/dL. Post-meal glucose should be below 140 mg/dL. HbA1c should be below 5.7%.
What prediabetes and diabetes numbers look like. Prediabetes is HbA1c 5.7% to 6.4%. Diabetes is HbA1c 6.5% or higher.
Age-specific advice: what a 60-year-old with high sugar needs versus a 25-year-old. Older adults need regular eye and foot exams, and careful medication management to prevent hypoglycemia. Young adults should focus aggressively on weight loss, regular intensive exercise, and potential disease reversal.
Indian foods to eat for high blood sugar. Bitter gourd (karela), fenugreek seeds (methi), moong dal, bajra, ragi (finger millet), spinach (palak), jamun, amla, whole wheat chapati (in moderation), and buttermilk (chaas).
Indian foods to avoid for high blood sugar. Refined sugar, jaggery, honey, white rice, maida (refined flour) items like naan, sweets like gulab jamun or jalebi, deep-fried snacks like samosas, sugary mangoes, and potatoes (in large amounts).
When to visit a doctor and which specialist. See an Endocrinologist if fasting sugar is consistently above 126 mg/dL, post-meal is above 200 mg/dL, or if experiencing frequent urination, unexplainable weight loss, or excessive thirst.

Section 2 — Cholesterol and Heart Health
Normal ranges for LDL, HDL, triglycerides, total cholesterol. Total cholesterol < 200 mg/dL, LDL < 100 mg/dL (lower if high risk), HDL > 40 mg/dL for men and > 50 mg/dL for women, Triglycerides < 150 mg/dL.
What high and low values mean for different ages. High LDL causes plaque buildup. Low HDL means reduced natural protection against plaque. High triglycerides often correlate with high carb intake and diabetes risk.
Indian foods to eat for high cholesterol. Oats, barley, rajma (kidney beans), chana (chickpeas), baingan (eggplant), bhindi (okra), walnuts, almonds, flaxseeds (alsi), garlic, and cooking oils like mustard oil or olive oil in moderation.
Indian foods to avoid for high cholesterol. Ghee (in large amounts), butter, vanaspati (dalda), red meat, deep-fried items like pakoras or puris, full-fat milk/paneer, coconut oil, and rich curries with heavy cream.
Warning signs that need same-day cardiology visit. Severe chest pain, tightness or pressure in the chest, pain radiating to the left arm or jaw, shortness of breath, sudden severe dizziness, excessive sweating for no reason.

Section 3 — Kidney Function
Normal ranges for creatinine, urea, eGFR. Serum creatinine: 0.7 to 1.3 mg/dL for men, 0.6 to 1.1 mg/dL for women. Blood Urea Nitrogen (BUN): 7 to 20 mg/dL. eGFR: > 90 mL/min/1.73m2.
What declining kidney function looks like at different stages. Mild decrease in eGFR (60-89) may have no symptoms. Moderate to severe drop implies chronic kidney disease. Very high creatinine (>2.0) requires immediate attention.
Indian foods safe for kidney patients. Cauliflower (gobi), cabbage (patta gobi), bell peppers (shimla mirch), bottle gourd (lauki), ridge gourd (turai), apple, papaya, white rice (if phosphorus restricted).
Indian foods kidney patients must avoid. Star fruit, high potassium foods like bananas, coconut water, oranges, sweet potatoes, spinach (palak), tomatoes, processed meat, salted snacks (namkeen, papad), and pickles (achar).
When to visit a nephrologist. If eGFR drops below 60, if creatinine is steadily increasing, if there is significant protein in urine, or swelling in legs/ankles combined with high blood pressure.

Section 4 — Liver Function
Normal ranges for ALT, AST, bilirubin, albumin. ALT: 7 to 55 U/L. AST: 8 to 48 U/L. Total Bilirubin: 0.1 to 1.2 mg/dL. Albumin: 3.5 to 5.0 g/dL.
What elevated liver enzymes mean. High ALT/AST suggests liver inflammation or damage (fatty liver, hepatitis, alcohol-related). High bilirubin indicates jaundice. Low albumin suggests severe chronic liver disease.
Indian foods that support liver health. Turmeric (haldi), garlic, green tea, amla (Indian gooseberry), lemon water, leafy greens, walnuts, and bitter gourd.
Indian foods that damage the liver. Alcohol (strictly avoid), excessive sugar and sweets (causes fatty liver), deep-fried foods, red meat, processed foods with high fructose corn syrup.
Warning signs of serious liver disease. Yellowing of eyes or skin (jaundice), severe abdominal pain and swelling (ascites), dark urine, pale stools, chronic fatigue, vomiting blood or black stools.

Section 5 — Thyroid
Normal TSH, T3, T4 ranges. TSH: 0.4 to 4.0 mIU/L. Free T3: 2.3 to 4.1 pg/mL. Free T4: 0.9 to 2.4 ng/dL.
Difference between hypothyroid and hyperthyroid. Hypothyroidism (high TSH, low T4): weight gain, fatigue, feeling cold, hair loss. Hyperthyroidism (low TSH, high T4): weight loss, rapid heartbeat, feeling hot, anxiety.
Age and gender specific thyroid advice — women over 40 are at higher risk. Women should test TSH regularly as pregnancy, menopause, and aging affect thyroid function significantly.
Indian foods for hypothyroid patients. Iodized salt, roasted makhana (fox nuts), eggs, fish, dairy (milk, curd), pumpkin seeds, and cooked vegetables.
Indian foods and things hypothyroid patients must avoid. Raw cruciferous vegetables (cabbage, cauliflower, broccoli), soy products (soybean, tofu, soya chunks), excessive caffeine, and millet (in large amounts without iodine).
Indian foods for hyperthyroid patients. Cruciferous vegetables (cabbage, cauliflower) can actually help block excess hormone production. Avoid excess iodine (iodized salt restriction sometimes needed).

Section 6 — Blood Counts CBC
Normal hemoglobin ranges for men and women by age group. Men: 13.5 to 17.5 g/dL. Women: 12.0 to 15.5 g/dL. Lower in pregnancy.
What anemia looks like and how severe it can get. Low hemoglobin (<10) causes severe fatigue, pale skin, shortness of breath. Very low (<7) may require a blood transfusion.
Normal WBC and what high or low WBC means. Normal WBC: 4,500 to 11,000 cells/mcL. High means active infection or inflammation. Low means weakened immunity (viral infections, certain medications).
Normal platelet count and danger levels. Normal: 150,000 to 450,000 /mcL. Below 50,000 is dangerous. Below 20,000 requires hospitalization due to bleeding risk (common in severe Dengue).
Indian foods rich in iron for anemia. Spinach (palak), amaranth leaves (chaulai), beetroot (chukandar), dates (khajoor), jaggery (gur), raisins (kishmish), ragi, moong dal, liver (if non-vegetarian).
Foods that block iron absorption that Indians commonly eat. Tea and coffee (especially right after a meal), excessive dairy (calcium blocks iron), high phytate foods (unsoaked beans/lentils).

Section 7 — Heart Tests ECG and Echo
What a normal ejection fraction looks like. Normal EF is 50% to 70%. Indicates how well the heart pumps blood. Below 40% suggests heart failure.
What ST changes on ECG mean. ST elevation often indicates an acute heart attack. ST depression suggests ischemia (reduced blood flow to heart muscle).
What left ventricular hypertrophy means. Thickening of the heart wall, usually due to long-term uncontrolled high blood pressure.
What pericardial effusion means. Fluid buildup around the heart. Can be mild, but severe cases prevent the heart from beating properly.
When these findings need same-day emergency visit. Any ST elevation, new bundle branch blocks with chest pain, EF below 30% with severe breathlessness.
Lifestyle and diet for heart patients in India. Low salt diet (avoid pickles, papad), daily brisk walk for 30-45 mins, stress reduction (yoga/pranayama), avoid trans fats (vanaspati/dalda), eat more fruits and vegetables like lauki and garlic.

Section 8 — MRI and CT Scan Reports
Common terms found in MRI reports and what they mean for action — lesion (abnormal tissue, requires investigation), edema (swelling, requires treatment), herniation (disc pressing on nerve, typical in spine MRI, needs orthopedic/neuro consult, avoid lifting weights), atrophy (shrinking of tissue, seen in brain MRI of older adults), infarct (stroke, dead tissue, emergency if acute).
Which MRI findings need neurologist today versus orthopedic in two weeks versus no urgency. Acute infarct (stroke) or mass with severe edema needs immediate ER/Neurologist. Mild disc bulge (spine) needs physiotherapy/Orthopedic in a few weeks.
CT scan findings that need immediate action. Acute bleeding in the brain (hemorrhage), large tumors, bowel obstruction, acute appendicitis, pulmonary embolism.

Section 9 — Vitamins and Minerals
Vitamin D normal range and deficiency levels. Normal: 30 to 100 ng/mL. Insufficiency: 20-29 ng/mL. Deficiency: < 20 ng/mL. Very common in India due to sun avoidance/pollution.
Vitamin B12 normal range and why vegetarians in India are commonly deficient. Normal: 200 to 900 pg/mL. Found mainly in animal products, so pure vegetarians and vegans are high risk. Causes nerve damage and fatigue.
Iron, Calcium, Potassium, Sodium, Uric Acid normal ranges. Uric acid: 3.5-7.2 mg/dL. Calcium: 8.5-10.2 mg/dL.
Indian foods to correct each deficiency. Vitamin D: sunlight exposure, fortified milk, egg yolks, mushrooms. B12: milk, curd, paneer, eggs. Uric acid: limit purine-rich foods (red meat, certain dals like masoor), drink plenty of water.
When supplements are needed versus food alone is enough. Severe B12 deficiency (<150) needs injections. Severe Vitamin D (<10) needs high dose sachets. Dietary changes alone are too slow for severe deficiencies.

Section 10 — Prescriptions
How to read whether a prescription is for a chronic condition or an acute condition. Chronic: given for 30/90 days (e.g., Telmisartan for BP, Metformin for diabetes, Thyroxine). Acute: given for 3, 5, or 7 days (e.g., Paracetamol, antibiotics).
What chronic condition prescriptions mean for action. Take daily at the same time. Never skip. Do not stop even if feeling fine without consulting the doctor.
What antibiotic prescriptions mean. Complete the full 3, 5, or 7-day course even if fever goes away on day 2. Incomplete courses cause antibiotic resistance.
Medicines that should never be stopped suddenly. Blood pressure medicines, beta blockers, antidepressants, steroids, anti-seizure medications.
When a prescription suggests the patient needs urgent follow-up. Doctor has written 'SOS' for chest pain (e.g., Sorbitrate) or prescribed very high dose antibiotics with a scheduled review in 2 days.

Section 11 — Urine Test
Normal urine test values. Color: pale yellow, clear. Protein: absent/trace. Glucose: absent. Blood: absent. Pus cells: 0-5 /HPF.
What protein in urine means. Kidney concern. Early sign of diabetic kidney disease or high blood pressure damage. Requires nephrologist consultation.
What blood in urine means. Urgent. Could be kidney stones, severe infection, or tumor. Needs an urologist.
What high glucose in urine means. Diabetes screening needed. Blood sugars are likely very high, spilling over into urine.
What UTI findings look like and action needed. High pus cells, presence of bacteria, nitrites positive. Need antibiotics. Drink plenty of water, cranberry juice, barley water. Seek doctor.

Section 12 — Age and Gender Specific General Rules
For patients above 60: gentler exercise recommendations (walking, gentle yoga), higher urgency for any abnormal finding, more frequent retest schedules. Focus on fall prevention. Pay attention to kidney and heart health.
For patients between 40 and 60: preventive focus. Time to get chronic diseases under control. Lifestyle change emphasis. Regular screening for diabetes, BP, cholesterol, cancer.
For patients below 40: aggressive lifestyle correction can reverse most findings like prediabetes or fatty liver. Lower urgency for slightly borderline values, but emphasis on immediate habit changes.
For women: iron deficiency (anemia) more common due to menstruation. Thyroid issues much more common. Bone density concerns (osteoporosis risk) after 40/menopause (need calcium/vitamin D).
For men: higher heart disease risk at a younger age. Higher uric acid risk. Focus on managing stress, avoiding smoking/alcohol, and regular cardiovascular exercise.
"""
