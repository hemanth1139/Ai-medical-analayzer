import os
import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
from config import GEMINI_MODEL
from components.sidebar import render_sidebar
from components.output_view import render_output
from utils.extractor import extract_content
from utils.agent import run_agent

# VIVA EXPLANATION:
# Vision: Gemini 1.5 Flash receives every document as images and reads it visually the same way a human reads a physical report. This handles all document types including ECG waveforms, MRI scans, handwritten prescriptions, and printed lab reports without any separate OCR step.
#
# LLM: Gemini reasons over the visual content along with the patient age and gender to generate personalized action-oriented advice. It never summarizes — it only tells the patient what to do next.
#
# RAG: A medical knowledge base covering 12 categories of conditions and Indian diet recommendations is embedded directly in the prompt. Gemini's 1 million token context window retrieves relevant facts internally when generating advice. This is the Retrieve Augment Generate pattern without a separate vector store.
#
# Agent: Gemini function calling is used to route each upload to the correct tool — analyze_text_document for typed PDFs and analyze_visual_document for images and scanned files. The LLM itself makes this routing decision, not hardcoded Python logic. This is a genuine agent observe decide act loop.

st.set_page_config(page_title="Patient Action Guide", page_icon="🏥", layout="wide")

if "result" not in st.session_state:
    st.session_state.result = None
if "analyzed" not in st.session_state:
    st.session_state.analyzed = False

@st.cache_resource
def get_model(api_key):
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(GEMINI_MODEL)

api_key = os.environ.get("GEMINI_API_KEY")
age, gender, language, uploaded_file = render_sidebar()

if uploaded_file is not None:
    if not api_key or api_key == "get_your_free_key_from_aistudio.google.com":
        st.error("Please set GEMINI_API_KEY in your .env file.")
    elif age is None:
        st.error("Please provide an age.")
    else:
        # Create a unique hash of the current input state to avoid unnecessary reruns
        current_state_hash = f"{uploaded_file.name}_{uploaded_file.size}_{age}_{gender}_{language}"
        
        if st.session_state.get("last_state_hash") != current_state_hash:
            st.session_state.result = None
            st.session_state.analyzed = False
            
            with st.spinner("Reading your medical document and preparing your action plan..."):
                extracted = extract_content(uploaded_file)
                if extracted.get("type") == "error":
                    st.error(extracted["message"])
                else:
                    try:
                        model = get_model(api_key)
                        result = run_agent(age, gender, language, extracted, model)
                        # Check if Gemini output an error dictionary
                        if "error" in result:
                            st.error(result["error"])
                        else:
                            st.session_state.result = result
                            st.session_state.analyzed = True
                            st.session_state.last_state_hash = current_state_hash
                    except Exception as e:
                        st.error(f"Error during analysis: {e}")

if st.session_state.analyzed and st.session_state.result is not None:
    render_output(st.session_state.result, language, age, gender)
else:
    st.write("## Welcome to the Patient Action Guide!")
    st.write("Upload any medical document to get simple, actionable health advice. Please fill in your age, gender, language, and provide a Gemini API key in the sidebar to get started.")
    st.write("### You can upload:")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info("📄 Blood Test PDFs")
        st.info("📋 Typen Prescriptions")
    with col2:
        st.info("🧠 MRI/CT Scan Reports")
        st.info("✍️ Handwritten Prescriptions")
    with col3:
        st.info("🫀 ECG or Echo Images")
        st.info("🦴 X-ray images")
