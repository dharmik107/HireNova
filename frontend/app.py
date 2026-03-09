import streamlit as st
import requests

BACKEND_URL = "http://localhost:8000"

st.set_page_config(page_title="HireNova", layout="wide", page_icon="🚀")

# Custom Premium CSS to make it look less simple
st.markdown("""
<style>
    /* Elegant Sidebar */
    [data-testid="stSidebar"] {
        box-shadow: 2px 0 10px rgba(0,0,0,0.02);
    }
    
    /* Stylized Headings */
    h1, h2, h3 {
        font-weight: 700 !important;
    }
    
    /* Modern Input Areas */
    .stTextArea textarea {
        border-radius: 8px;
        box-shadow: inset 0 1px 2px rgba(0,0,0,0.05);
        padding: 12px;
    }
    .stTextArea textarea:focus {
        border-color: #3b82f6;
        box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
    }
    
    /* Primary Action Buttons */
    .stButton>button[kind="primary"] {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%) !important;
        color: white !important;
        font-weight: 600 !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.5rem 1.5rem !important;
        transition: all 0.2s ease-in-out;
        box-shadow: 0 4px 6px -1px rgba(59, 130, 246, 0.4) !important;
    }
    .stButton>button[kind="primary"]:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 8px -1px rgba(59, 130, 246, 0.5) !important;
    }

    /* Small Red Delete Buttons (Secondary) */
    .stButton>button[kind="secondary"] {
        background: transparent !important;
        color: #ef4444 !important;
        border: 1px solid #fca5a5 !important;
        border-radius: 6px !important;
        padding: 0.1rem 0.4rem !important;
        font-size: 14px !important;
        transition: all 0.2s;
    }
    .stButton>button[kind="secondary"]:hover {
        background: #fee2e2 !important;
        border-color: #ef4444 !important;
    }
    
    /* Results Cards/Expanders */
    div.stExpander {
        border-radius: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        margin-top: 1rem;
    }
    
    /* Sub-cards for evaluation */
    .evaluation-card {
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid #e5e7eb;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
        margin-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session states
if "jd_text" not in st.session_state:
    st.session_state.jd_text = ""

# Function to fetch JDs
def fetch_jds():
    try:
        response = requests.get(f"{BACKEND_URL}/jds")
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return []

def delete_jd(jd_id):
    try:
        requests.delete(f"{BACKEND_URL}/jds/{jd_id}")
        st.success("Deleted successfully!")
        st.rerun()
    except Exception as e:
        st.error(f"Failed to delete: {e}")

saved_jds = fetch_jds()

# --- Sidebar Navigation ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/8112/8112521.png", width=60) # placeholder robot/resume icon
    st.markdown("### Menu")
    app_mode = st.radio(
        "Choose an Option:",
        ["1. Generate JD", "2. Evaluate CV"],
        index=0
    )
    
    st.markdown("---")
    st.markdown("### 🗂️ Saved Job Descriptions")
    if not saved_jds:
        st.caption("No Job Descriptions saved yet.")
    else:
        for jd in saved_jds:
            colA, colB = st.columns([4, 1])
            with colA:
                st.caption(f"**{jd['title']}** (ID: {jd['id']})")
            with colB:
                if st.button("🗑️", key=f"del_{jd['id']}", help="Delete JD"):
                    delete_jd(jd['id'])
    
    st.markdown("---")
    st.caption("v1.0 • Built with CrewAI & FastAPI")

# --- Main Title ---
st.title("🚀 HireNova")
st.markdown("**Discover elite talent at lightspeed.** Use our intelligent agents to write pristine Job Descriptions and schedule interviews instantly based on CV analysis.")
st.markdown("---")

# --- Page 1: Generate Job Description ---
if app_mode == "1. Generate JD":
    st.header("✨ Step 1: AI Job Description Generator")
    st.markdown("Provide a basic prompt and let our **Expert HR Agent** write a detailed, formatted job description for you.")
    
    job_prompt = st.text_area(
        "Job Prompt Requirements:",
        placeholder="e.g. I want a GenAI intern for Crovix. The location will be remote.",
        height=150
    )
    
    col1, col2, col3 = st.columns([1,2,1])
    with col1:
        generate_btn = st.button("Generate Job Description 🚀", type="primary")

    if generate_btn:
        if job_prompt:
            with st.spinner("Agent is actively crafting the description..."):
                try:
                    response = requests.post(f"{BACKEND_URL}/generate_jd", json={"prompt": job_prompt})
                    if response.status_code == 200:
                        data = response.json()
                        st.session_state.jd_text = data.get("content", "")
                        st.success(f"✅ Job Description '{data.get('title')}' Generated & Saved Successfully!")
                        st.rerun()
                    else:
                        st.error(f"Error from server: {response.text}")
                except Exception as e:
                    st.error(f"Connection Error: {e}. Is the backend running?")
        else:
            st.warning("Please enter a prompt first.")

    if st.session_state.jd_text:
        with st.expander("📄 View Last Generated Job Description", expanded=True):
            st.markdown(st.session_state.jd_text)


# --- Page 2: Evaluate Candidate Resume ---
elif app_mode == "2. Evaluate CV":
    st.header("🎯 Step 2: AI Profile Evaluation")
    st.markdown("Upload a candidate's CV. Our **Senior Technical Recruiter** and **HR Coordinator** agents will evaluate it against the active Job Description and draft a response.")
    
    if not saved_jds:
        st.warning("⚠️ No Job Descriptions found in database. Please generate one first.")
    else:
        # Create a dictionary mapping titles to contents
        jd_options = {f"ID {jd['id']}: {jd['title']}": jd['content'] for jd in saved_jds}
        selected_jd_title = st.selectbox("Select a Saved Job Description:", list(jd_options.keys()))
        selected_jd_content = jd_options[selected_jd_title]

        with st.expander("👁️ View Selected Job Description", expanded=False):
            st.markdown(selected_jd_content)

        st.markdown("#### Upload CV")
        uploaded_file = st.file_uploader("Must be .pdf or .docx format", type=["pdf", "docx"])
        
        if st.button("Evaluate Candidate 📊", type="primary"):
            if uploaded_file is None:
                st.warning("⚠️ Please upload a CV.")
            else:
                with st.spinner(f"Agents are analyzing candidate against '{selected_jd_title}'..."):
                    try:
                        # Prepare payload based on the file type
                        file_mime = "application/pdf" if uploaded_file.name.endswith('.pdf') else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), file_mime)}
                        data = {"job_description": selected_jd_content}
                        
                        response = requests.post(f"{BACKEND_URL}/evaluate_resume", data=data, files=files)
                        
                        if response.status_code == 200:
                            res_json = response.json()
                            result = res_json.get("result", {})
                            
                            st.success("✨ Evaluation Complete!")
                            st.balloons()
                            
                            # Display Results in premium columns
                            st.markdown("<br>", unsafe_allow_html=True)
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.markdown("""
                                <div class="evaluation-card">
                                    <h3 style="margin-top:0;">📋 Recruiter Review</h3>
                                    <p style="opacity: 0.8; font-size:14px;">Calculated Eligibility Index</p>
                                </div>
                                """, unsafe_allow_html=True)
                                st.markdown(result.get("evaluation", "No evaluation details returned."))
                            
                            with col2:
                                st.markdown("""
                                <div class="evaluation-card">
                                    <h3 style="margin-top:0;">✉️ HR Communications</h3>
                                    <p style="opacity: 0.8; font-size:14px;">Automated Draft Email Response</p>
                                </div>
                                """, unsafe_allow_html=True)
                                email_content = result.get("email", "No scheduler details returned.")
                                st.markdown(f"> {email_content}")
                                
                        else:
                            st.error(f"Error from server: {response.text}")
                    except Exception as e:
                         st.error(f"Connection Error: {e}")
