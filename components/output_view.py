import streamlit as st
import json
from config import HEALTH_STATUS_LEVELS

def get_text_content(plan_text, language):
    return plan_text

def render_output(result, language, age, gender):
    if "error" in result:
        st.error(result["error"])
        return

    # 1. Document Detected
    st.caption(f"Document Found: {result.get('document_type_detected', 'Unknown')}")
    
    # 2. Health Status
    status_val = result.get('health_status', 'Good')
    status_config = HEALTH_STATUS_LEVELS.get(status_val, HEALTH_STATUS_LEVELS["Good"])
    # Create HTML styled box
    html_status = f"""
    <div style="background-color: {status_config['color']}; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
        <h2 style="margin-top: 0; color: #333;">{status_config['emoji']} {status_val}</h2>
        <p style="font-size: 1.2rem; margin-bottom: 10px; color: #444;">{result.get('health_status_reason', '')}</p>
        <div style="background-color: rgba(255,255,255,0.5); padding: 10px; border-radius: 5px;">
            <strong>🧬 At your age ({age}):</strong> {result.get('age_specific_context', '')}
        </div>
    </div>
    """
    st.markdown(html_status, unsafe_allow_html=True)
    
    # NEW: Irreversible Timeline
    timeline_html = f"""
    <div style="background-color: #333333; color: white; padding: 15px; border-radius: 10px; margin-bottom: 20px; border-left: 5px solid #FF9800;">
        <h3 style="margin-top: 0; color: #FFA726;">⏳ The "Point of No Return"</h3>
        <p style="margin-bottom: 0;">{result.get('irreversible_timeline', 'No immediate permanent risk detected.')}</p>
    </div>
    """
    st.markdown(timeline_html, unsafe_allow_html=True)
    
    # NEW: Ayurveda Warning
    warning = result.get('ayurveda_warning', 'Safe')
    if warning.lower() != 'safe' and 'safe' not in warning.lower():
        ayurveda_html = f"""
        <div style="background-color: #FBE9E7; padding: 15px; border-radius: 10px; margin-bottom: 20px; border-left: 5px solid #D84315;">
            <h3 style="margin-top: 0; color: #D84315;">🌿 Ayurveda / Home Remedy Warning</h3>
            <p style="color: #444; margin-bottom: 0;"><strong>DANGER:</strong> {warning}</p>
        </div>
        """
        st.markdown(ayurveda_html, unsafe_allow_html=True)
    
    # 3. Doctor Visit
    needs_doctor = result.get('doctor_visit_needed', False)
    if needs_doctor:
        urgency = result.get('visit_urgency', '')
        if "Today" in urgency or "3 days" in urgency:
            doc_color = "#FFCDD2" # Red
        elif "2 weeks" in urgency:
            doc_color = "#FFE0B2" # Orange
        else:
            doc_color = "#FFF9C4" # Yellow
            
        doc_html = f"""
        <div style="background-color: {doc_color}; padding: 15px; border-radius: 10px; margin-bottom: 20px; border-left: 5px solid #E53935;">
            <h3 style="margin-top: 0; color: #333;">👨‍⚕️ Doctor Visit Required</h3>
            <p style="font-weight: bold; color: #444;">See: {result.get('doctor_type', 'General Physician')}</p>
            <p style="color: #444;">Urgency: {urgency}</p>
            <hr style="border-color: rgba(0,0,0,0.1);">
            <p style="color: #444; font-size: 0.9em;"><strong>Rule of Thumb:</strong> {result.get('when_to_see_doctor_rules', '')}</p>
        </div>
        """
        st.markdown(doc_html, unsafe_allow_html=True)
    else:
        st.success(f"👨‍⚕️ No doctor visit needed right now. \n\n**Rule of Thumb:** {result.get('when_to_see_doctor_rules', '')}")
        
    # NEW: Cost Guard
    cost_html = f"""
    <div style="background-color: #E8F5E9; padding: 10px 15px; border-radius: 10px; margin-bottom: 20px; border-left: 5px solid #4CAF50;">
        <p style="margin: 0; color: #2E7D32;"><strong>💰 Cost Guard Tip:</strong> {result.get('cost_guard_suggestion', 'No specific test savings identified.')}</p>
    </div>
    """
    st.markdown(cost_html, unsafe_allow_html=True)
        
    st.markdown("---")
        
    # 4. Foods to Eat
    with st.expander("🥦 Foods to Eat"):
        for food in result.get('foods_to_eat', []):
            st.markdown(f"- {food}")
            
    # 5. Foods to Avoid
    with st.expander("❌ Foods to Avoid"):
        for food in result.get('foods_to_avoid', []):
            st.markdown(f"- {food}")
            
    # 6. Daily Habits
    with st.expander("🏃 Daily Habits"):
        for i, habit in enumerate(result.get('daily_habits', []), 1):
            st.markdown(f"{i}. {habit}")
            
    # 7. When to Retest
    with st.expander("📅 When to Retest"):
        for test in result.get('retest_schedule', []):
            st.markdown(f"- {test}")
            
    # 8. Warning Signs (Always visible)
    st.markdown("### ⚠️ Warning Signs")
    for sign in result.get('warning_signs', []):
        st.markdown(f"<span style='color: red; font-weight: bold;'>{sign}</span>", unsafe_allow_html=True)

    st.write("---")
    
    # NEW: Questions for Doctor
    if result.get('questions_for_doctor'):
        st.markdown("### 🗣️ What to Ask Your Doctor")
        for q in result.get('questions_for_doctor', []):
            st.markdown(f"- **{q}**")
            
    col1, col2 = st.columns(2)
    # NEW: Myth Buster
    with col1:
        st.markdown("### 🛑 Myth vs Fact")
        st.info(result.get('local_myth_buster', 'No specific myth found.'))
        
    # NEW: Scariest Word Translated
    with col2:
        st.markdown("### 📖 Medical Jargon Translated")
        st.success(result.get('scariest_word_translated', 'No complex jargon found.'))

    st.write("---")
    
    # NEW: Explainable AI - Traceability Matrix
    st.markdown("### 🔍 Explainable AI (Traceability Matrix)")
    st.markdown("This section maps the AI's advice directly to the raw data found in your report to ensure transparency and trust.")
    
    matrix = result.get('traceability_matrix', [])
    if matrix:
        # Create a nice HTML table for traceability
        table_html = "<table style='width: 100%; border-collapse: collapse; border: 1px solid #ddd; margin-bottom: 20px;'>"
        table_html += "<tr style='background-color: #f2f2f2;'><th style='padding: 12px; border: 1px solid #ddd;'>AI Advice Given</th><th style='padding: 12px; border: 1px solid #ddd;'>Triggered By (Exact Report Quote)</th></tr>"
        
        for item in matrix:
            advice = item.get('advice_given', '')
            quote = item.get('exact_report_quote', '')
            table_html += f"<tr><td style='padding: 12px; border: 1px solid #ddd;'>{advice}</td><td style='padding: 12px; border: 1px solid #ddd; font-family: monospace; background-color: #fff9e6;'>{quote}</td></tr>"
        
        table_html += "</table>"
        st.markdown(table_html, unsafe_allow_html=True)
    else:
        st.info("No explicit traceability mapping generated for this document.")

    st.write("---")

    
    # 9. Download Button
    plan_text = f"PATIENT ACTION PLAN (Age: {age}, Gender: {gender})\n\n"
    plan_text += f"Document: {result.get('document_type_detected')}\n"
    plan_text += f"Status: {result.get('health_status')} - {result.get('health_status_reason')}\n"
    plan_text += f"Age Context: {result.get('age_specific_context')}\n\n"
    
    if result.get('doctor_visit_needed'):
        plan_text += f"DOCTOR VISIT: {result.get('doctor_type')} ({result.get('visit_urgency')})\n"
    else:
        plan_text += f"DOCTOR VISIT: Not Required Right Now\n"
        
    plan_text += f"Doctor Rules: {result.get('when_to_see_doctor_rules')}\n\n"
        
    plan_text += "FOODS TO EAT:\n" + "\n".join([f"- {f}" for f in result.get('foods_to_eat', [])]) + "\n\n"
    plan_text += "FOODS TO AVOID:\n" + "\n".join([f"- {f}" for f in result.get('foods_to_avoid', [])]) + "\n\n"
    plan_text += "DAILY HABITS:\n" + "\n".join([f"- {h}" for h in result.get('daily_habits', [])]) + "\n\n"
    plan_text += "QUESTIONS FOR DOCTOR:\n" + "\n".join([f"- {q}" for q in result.get('questions_for_doctor', [])]) + "\n\n"
    plan_text += f"POINT OF NO RETURN:\n{result.get('irreversible_timeline', '')}\n\n"
    plan_text += f"AYURVEDA WARNING:\n{result.get('ayurveda_warning', '')}\n\n"
    plan_text += f"COST GUARD PREDICTION:\n{result.get('cost_guard_suggestion', '')}\n\n"
    plan_text += f"MYTH BUSTER:\n{result.get('local_myth_buster', '')}\n\n"
    plan_text += f"MEDICAL JARGON TRANSLATED:\n{result.get('scariest_word_translated', '')}\n\n"
    plan_text += "WARNING SIGNS:\n" + "\n".join([f"- {s}" for s in result.get('warning_signs', [])]) + "\n"
    
    st.download_button(
        label="Download Action Plan (.txt)",
        data=plan_text,
        file_name=f"action_plan_{age}_{gender.lower()}.txt",
        mime="text/plain"
    )

    if result.get("fhir_bundle"):
        st.download_button(
            label="Export to EHR (FHIR)",
            data=json.dumps(result["fhir_bundle"], indent=2),
            file_name="patient_fhir_data.json",
            mime="application/json",
            type="primary"
        )
