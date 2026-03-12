import streamlit as st
import requests
import re
import markdown

BACKEND_URL = "http://localhost:8000"

st.set_page_config(page_title="HireNova", layout="wide", page_icon="🚀")

# --- Custom Premium CSS ---
st.markdown("""
<style>
    /* Elegant Sidebar */
    [data-testid="stSidebar"] {
        box-shadow: 2px 0 10px rgba(0,0,0,0.02);
    }
    
    /* Stylized Headings */
    h1, h2, h3 { font-weight: 700 !important; }
    
    /* Primary Action Buttons */
    .stButton>button[kind="primary"] {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%) !important;
        color: white !important;
        font-weight: 500 !important;
        border: none !important;
        border-radius: 6px !important;
        padding: 0.3rem 0.8rem !important;
        font-size: 14px !important;
        transition: all 0.2s ease-in-out;
        box-shadow: 0 4px 6px -1px rgba(59, 130, 246, 0.4) !important;
    }
    .stButton>button[kind="primary"]:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 8px -1px rgba(59, 130, 246, 0.5) !important;
    }

    /* Small Red Delete Buttons */
    .stButton>button[kind="secondary"] {
        background: transparent !important;
        color: #ef4444 !important;
        border: 1px solid #fca5a5 !important;
        border-radius: 6px !important;
        font-size: 14px !important;
    }
    
    /* Combined Status Box */
    .combined-status {
        font-size: 24px;
        font-weight: 800;
        padding: 18px 30px;
        border-radius: 12px;
        margin: 1.5rem 0;
        display: inline-block;
        border: 2px solid;
    }
    .status-match-eligible { 
        background: rgba(6, 95, 70, 0.1); 
        color: #34d399; 
        border-color: #065f46;
    }
    .status-match-not-eligible { 
        background: rgba(127, 29, 29, 0.1); 
        color: #f87171; 
        border-color: #7f1d1d;
    }

    /* Detail Boxes with Bullet Support */
    .detail-box {
        background: #1e1e1e;
        border-left: 5px solid #3b82f6;
        padding: 1.5rem;
        border-radius: 8px;
        margin-bottom: 1.2rem;
        color: #f3f4f6;
        line-height: 1.6;
        border: 1px solid #374151;
        border-left: 5px solid #3b82f6;
    }
    .detail-box ul { margin-top: 5px; margin-bottom: 5px; padding-left: 20px; }
    .detail-box li { margin-bottom: 4px; }

    /* Email Composer */
    .email-container {
        background: #1e1e1e;
        border: 1px solid #374151;
        border-radius: 8px;
        overflow: hidden;
        margin-top: 1rem;
    }
    .email-header {
        background: #2d2d2d;
        padding: 12px 16px;
        border-bottom: 1px solid #374151;
    }
    .email-row { margin-bottom: 4px; font-size: 14px; }
    .email-label { color: #9ca3af; width: 60px; display: inline-block; }
    .email-body {
        padding: 20px;
        font-family: 'Inter', sans-serif;
        line-height: 1.6;
        white-space: pre-wrap;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session states
if "jd_text" not in st.session_state:
    st.session_state.jd_text = ""

def parse_evaluation(text):
    """Parses evaluation result text into structured sections with bullet support."""
    sections = {
        "Technical Alignment": "",
        "Experience Depth": "",
        "Role Fit": "",
        "Strengths": "",
        "Critical Gaps": "",
        "Final Verdict": "",
        "Score": "N/A",
        "Eligible": "False"
    }

    # Clean the text of all bold markers for header detection
    clean_text_for_parsing = text.replace("**", "")

    # Extract Score
    score_match = re.search(r"(?:Score|Index|Result|Recommendation)?[:*\s]*(\d{1,3}%)", text, re.IGNORECASE)
    if not score_match:
        score_match = re.search(r"(\d{2,3}%)", text)
        
    if score_match:
        sections["Score"] = score_match.group(1)

    # Extract Eligibility
    eligibility_match = re.search(r"Eligible:\s*(True|False)", text, re.IGNORECASE)
    if eligibility_match:
        sections["Eligible"] = eligibility_match.group(1)

    # Parse sections
    current_key = None
    lines = text.split('\n')
    header_patterns = ["Technical Alignment", "Experience Depth", "Role Fit", "Strengths", "Critical Gaps", "Final Verdict"]
    
    for line in lines:
        stripped = line.strip()
        if not stripped: continue
        
        # Check for section headers
        found_header = False
        line_no_bold = stripped.replace("**", "")
        for pattern in header_patterns:
            if line_no_bold.lower().startswith(pattern.lower()):
                current_key = pattern
                found_header = True
                
                # Extract initial content if header has a colon
                if ":" in line_no_bold:
                    content = line_no_bold.split(":", 1)[-1].strip()
                    # Only add if it's not just the header name again
                    if content and content.lower() != pattern.lower():
                        sections[current_key] = content + "\n"
                break
        
        if not found_header and current_key:
            # Preserve bullets and clean residual leading bolding/artifacts
            cleaned_line = stripped
            if cleaned_line.startswith("**"):
                # Check if it's a bold header that we missed
                potential_header = cleaned_line.split(":", 1)[0].replace("**", "").strip()
                if any(potential_header.lower() == h.lower() for h in header_patterns):
                    continue # Skip as it's just a header line
                    
            if stripped.startswith("*") or stripped.startswith("-") or stripped.startswith("•"):
                sections[current_key] += f"\n{stripped}"
            else:
                sections[current_key] += f" {stripped}"

    # Final cleanup of each section to remove leading formatting garbage
    for key in sections:
        if key not in ["Score", "Eligible"]:
            # Remove leading colons, extra bold markers, or repeating headers
            val = sections[key].strip()
            if val.startswith(":"): val = val[1:].strip()
            sections[key] = val

    return sections

def parse_email(text):
    """Parses To, Subject, and Body from the email agent output."""
    data = {"To": "N/A", "Subject": "N/A", "Body": text}
    clean_text = text.replace("**", "")
    lines = clean_text.split('\n')
    
    for i, line in enumerate(lines):
        item = line.strip()
        if item.lower().startswith("to:"):
            data["To"] = item.split(":", 1)[-1].strip()
        elif item.lower().startswith("subject:"):
            data["Subject"] = item.split(":", 1)[-1].strip()
        elif item.lower().startswith("body:"):
            data["Body"] = "\n".join(lines[i+1:]).strip()
            return data
            
    # Fallback Body extraction
    body_lines = []
    capture = False
    for line in lines:
        if capture: body_lines.append(line)
        if any(line.lower().startswith(h) for h in ["to:", "subject:"]):
            capture = True
    if body_lines:
        data["Body"] = "\n".join(body_lines).strip()
    return data

# --- Data Helpers ---
def fetch_jds():
    try:
        r = requests.get(f"{BACKEND_URL}/jds")
        return r.json() if r.status_code == 200 else []
    except: return []

def delete_jd(jd_id):
    try:
        requests.delete(f"{BACKEND_URL}/jds/{jd_id}")
        st.rerun()
    except Exception as e: st.error(f"Error: {e}")

saved_jds = fetch_jds()

# --- Sidebar ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/8112/8112521.png", width=60)
    st.markdown("### Menu")
    app_mode = st.radio("Choose Option:", ["1. Generate JD", "2. Evaluate CV"])
    st.markdown("---")
    st.markdown("### 🗂️ Saved JDs")
    for jd in saved_jds:
        colA, colB = st.columns([4, 1])
        colA.caption(f"**{jd['title']}** (ID: {jd['id']})")
        if colB.button("🗑️", key=f"del_{jd['id']}"): delete_jd(jd['id'])

# --- Header ---
st.title("🚀 HireNova")
st.markdown("### Discover Elite Talent at Lightspeed")
st.markdown("---")

if app_mode == "1. Generate JD":
    st.header("✨ AI Job Description Generator")
    job_prompt = st.text_area("Prompt:", placeholder="e.g. GenAI intern role at Crovix...", height=150)
    if st.button("Generate JD 🚀", type="primary"):
        if job_prompt:
            with st.spinner("Writing JD..."):
                r = requests.post(f"{BACKEND_URL}/generate_jd", json={"prompt": job_prompt})
                if r.status_code == 200:
                    st.session_state.jd_text = r.json().get("content", "")
                    st.rerun()
        else: st.warning("Enter prompt first.")

    if st.session_state.jd_text:
        st.markdown("### 📄 Generated Job Description")
        st.markdown(f"<div style='background: #1e1e1e; padding: 30px; border-radius: 12px; border: 1px solid #374151;'>{markdown.markdown(st.session_state.jd_text)}</div>", unsafe_allow_html=True)

elif app_mode == "2. Evaluate CV":
    st.header("🎯 AI Profile Evaluation")
    if not saved_jds:
        st.warning("Generate a JD first.")
    else:
        jd_options = {f"ID {j['id']}: {j['title']}": j['content'] for j in saved_jds}
        sel_title = st.selectbox("Select JD:", list(jd_options.keys()))
        uploaded_file = st.file_uploader("Upload CV (.pdf, .docx)", type=["pdf", "docx"])
        
        if st.button("Evaluate Candidate 📊", type="primary") and uploaded_file:
            with st.spinner("Analyzing..."):
                mime = "application/pdf" if uploaded_file.name.endswith('.pdf') else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), mime)}
                r = requests.post(f"{BACKEND_URL}/evaluate_resume", data={"job_description": jd_options[sel_title]}, files=files)
                
                if r.status_code == 200:
                    res = r.json().get("result", {})
                    eval_p = parse_evaluation(res.get("evaluation", ""))
                    email_p = parse_email(res.get("email", ""))
                    
                    st.success("Done!")
                    st.balloons()
                    
                    # Highlight Status
                    is_eligible = "true" in eval_p['Eligible'].lower()
                    cls = "status-match-eligible" if is_eligible else "status-match-not-eligible"
                    txt = "ELIGIBLE" if is_eligible else "NOT ELIGIBLE"
                    st.markdown(f"<div class='combined-status {cls}'>{eval_p['Score']} — {txt}</div>", unsafe_allow_html=True)
                    
                    t1, t2 = st.tabs(["📋 Evaluation Report", "✉️ Draft Email"])
                    with t1:
                        def show_box(title, info, icon):
                            if info.strip():
                                st.markdown(f"#### {icon} {title}")
                                # Pre-render the content to HTML to ensure it wraps correctly
                                inner_html = markdown.markdown(info)
                                st.markdown(f"""
                                <div class='detail-box'>
                                    {inner_html}
                                </div>
                                """, unsafe_allow_html=True)

                        show_box("Technical Alignment", eval_p["Technical Alignment"], "⚙️")
                        show_box("Role Fit", eval_p["Role Fit"], "📌")
                        show_box("Strengths", eval_p["Strengths"], "✅")
                        show_box("Critical Gaps", eval_p["Critical Gaps"], "⚠️")
                        show_box("Final Verdict", eval_p["Final Verdict"], "⚖️")

                    with t2:
                        st.markdown(f"""
                        <div class="email-container">
                            <div class="email-header">
                                <div class="email-row"><span class="email-label">To:</span> <b>{email_p['To']}</b></div>
                                <div class="email-row"><span class="email-label">Subject:</span> <b>{email_p['Subject']}</b></div>
                            </div>
                            <div class="email-body">{email_p['Body']}</div>
                        </div>
                        """, unsafe_allow_html=True)
                else: st.error("Server Error")
