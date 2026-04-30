import streamlit as st

def render_sidebar():
    with st.sidebar:
        st.title("Patient Action Guide 🏥")
        st.write("Upload your medical report and get your personal action plan")
        
        st.write("---")
        

        
        age = st.number_input("Age", min_value=1, max_value=110, step=1, value=30)
        gender = st.selectbox("Gender", options=["Male", "Female", "Other"])
        language = st.selectbox("Language", options=["English", "Tamil"])
        
        st.write("---")
        
        uploaded_file = st.file_uploader(
            "Upload Report", 
            type=["pdf", "png", "jpg", "jpeg"],
            help="Upload blood test, MRI, ECG, X-ray, prescription, or any medical document"
        )
        

        st.caption("Disclaimer: This app does not replace your doctor and always consult a medical professional.")
        
        return age, gender, language, uploaded_file
