import os
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, LLM
from crewai.tools import tool
from duckduckgo_search import DDGS

# Load environment variables
load_dotenv()

# Initialize Groq LLM using OpenAI native provider to avoid litellm dependency
llm = LLM(
    model="openai/llama-3.1-8b-instant",
    api_key=os.environ.get("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
    temperature=0.0
)

# Second LLM for creative layout variation (JD drafting)
llm_generation = LLM(
    model="openai/llama-3.1-8b-instant",
    api_key=os.environ.get("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
    temperature=0.4
)

def generate_jd(prompt: str, domain: str = None, seniority: str = None) -> str:
    """Generates a Job Description from a simple prompt using CrewAI."""
    
    # 0. Domain & Seniority Classification
    domain_provided = domain is not None and domain.lower() not in ["auto-detect", "none", ""]
    seniority_provided = seniority is not None and seniority.lower() not in ["auto-detect", "none", ""]
    
    # Defaults
    if not domain_provided:
        domain = "General"
    if not seniority_provided:
        seniority = "Experienced"
        
    # Only call LLM to classify if full context is missing
    if not (domain_provided and seniority_provided):
        classification_prompt = f"""
        Analyze the hiring manager's prompt: "{prompt}"
        1. **Identify exact Domain/Industry** (e.g., Tech, Marketing, Finance, Legal, Healthcare, HR).
        2. **Determine target Seniority** (e.g., Intern, Entry-Level, Experienced, Senior, Director).

        Output STRICTLY in this format:
        Domain: <Specific Domain>
        Seniority: <Specific Seniority>
        """
        
        try:
            class_res = llm.call(classification_prompt)
            import re
            d_match = re.search(r'Domain:\s*(.+)', class_res, re.IGNORECASE)
            s_match = re.search(r'Seniority:\s*(.+)', class_res, re.IGNORECASE)
            
            if d_match and not domain_provided: domain = d_match.group(1).strip()
            if s_match and not seniority_provided: seniority = s_match.group(1).strip()
        except Exception as e:
             pass

    # 1. Layered Web Search (DuckDuckGo)
    research_context = ""
    queries = [
        f'"{prompt}" skills 2026',
        f'"{prompt}" job description responsibilities',
        f'"tools used by" "{prompt}" engineers'
    ]
    
    # Run structured 3-Query Layered search Extraction
    for q in queries:
         try:
             search_results = DDGS().text(q, max_results=3)
             if search_results:
                  context_items = [f"Source: {r.get('title', 'Role Info')}\nSnippet: {r.get('body', '')}" for r in search_results]
                  research_context += f"=== Search Results for: {q} ===\n" + "\n\n".join(context_items) + "\n\n"
         except Exception:
              pass
              
    if not research_context.strip():
        research_context = f"Standard industry qualifications apply for a {prompt} role."

    # 2. Generate Job Description in One Shot
    generate_prompt = f"""
    Create a concise, structured, and professional job description based on these details:
    - Hiring Manager Prompt: "{prompt}"
    - Classified Domain: {domain}
    - Classified Seniority: {seniority}
    
    Provided Research Context:
    \"\"\"
    {research_context}
    \"\"\"

    STRICT CONSTRAINTS & ACCURACY RULES:
    1. **Layer 2: Structured Extraction**: Read the provided Research Context batches and explicitly isolate bullet points for **Skills**, **Tools**, and **Responsibilities** before formulating the final layout text. Use specific tool titles (e.g., Scikit-Learn/TensorFlow for AI/ML; LangChain/HuggingFace *only* if role is explicitly Generative AI).
    2. **Differentiate strictly on hiring prompt "{prompt}"**:
       - **If Agentic AI**: Focus on autonomous systems, tool calling, memory management, and workflow agents.
       - **If GenAI**: Focus on LLMs, Prompt engineering, embeddings, and vector databases.
       - **If AI/ML**: Focus on data-preprocessing, regressions, model architectures, and training workflows.
    3. **No Placeholders**: **NEVER output square brackets like `[...]` or `[Insert ...]`**. Deduce reasonable constants from standard practice (e.g., "Remote", "To be discussed", "XYZ Corp", "Competitive").
    4. **Tone**: Keep it highly professional and engaging.

    EXACT LAYOUT INSTRUCTIONS (Follow this structure strictly):
    1. **Job Title**: The exact role title formatted as an H1 heading (e.g. `# GenAI Intern`).
    2. **Company**: Must be formatted exactly as `**Company:** [Calculated Company Name]` on a new line.
    3. **Location & Work Mode**: Must be formatted exactly as `**Location & Work Mode:** [Calculated Location] | [Remote/Hybrid/On-site]` on a new line.
    4. **Duration**: Must be formatted exactly as `**Duration:** [Calculated Duration]` on a new line.
    5. **Stipend**: Must be formatted exactly as `**Stipend:** [Calculated Value]` on a new line.
    6. **Spacing**: ALWAYS leave a blank line after headers 1-5.
    
    7. **About the Company**: Use `### About the Company` as a heading. Add 1-2 lines describing general domain setup.
    8. **Eligibility**: Use `### Eligibility` as a heading. Itemize 1-2 lines on degree requirement/year level (e.g., Final Year CS/AI students).
    9. **Key Responsibilities**: Use `### Key Responsibilities` as a heading. Then a blank line, then 4-5 bullet points of core tasks tailored strictly to the matched experience level.
    10. **Skills & Tools**: Use `### Skills & Tools` as a heading. Provide exactly 4-5 bullet points prioritizing specific modern framework titles.
    11. **What you will learn**: Use `### What you will learn` as a heading. **OMIT completely if non-internship.**
    12. **How to Apply**: Use `### How to Apply` as a heading. Add brief instructions.

    Follow this structure strictly with blank lines between headings and content.
    """
    
    try:
        result_str = llm_generation.call(generate_prompt)
    except Exception as e:
        result_str = f"Error generating JD: {str(e)}"

    # Post-processing to enforce strict layout omissions
    import re
    result_str = re.sub(r'\*\*(Duration|Stipend):\*\*\s*(Not Specified|None|N/A|Permanent|Unspecified)\b', '', result_str, flags=re.IGNORECASE)
    
    return result_str.strip()

def evaluate_candidate(jd: str, resume_text: str) -> dict:
    """Evaluates a resume against a JD and schedules an interview if applicable."""
    
    evaluate_prompt = f"""
    Review the following Resume against the provided Job Description with extreme scrutiny. 
    Calculate a matching score out of 100 based on technical skills, professional experience, and alignment.

    CRITICAL INSTRUCTIONS:
    1. **Context-Aware Evaluation**: Identify if the JD is for an Internship/Entry-level or Experienced role.
    2. **Experience Scoring**: 
       - For Experienced Roles: If 3+ years required and candidate has <3 years, deduct points. 0 experience = NOT ELIGIBLE.
       - For Internships: Do not penalize for lack of years. Rate on skills and projects.
    3. **Output Structure**: Provide a structured breakdown EXACTLY using these Headers:
       - **Technical Alignment**: How well they know the stack.
       - **Role Fit**: Level match.
       - **Strengths**: 3-4 bullets.
       - **Critical Gaps**: What are they missing.
       - **Final Verdict**: Justification concluding with `Eligible: True/False`.

    --- EVALUATION DONE ---

    Next, draft a short email to the candidate:
    1. If Eligible: True: 'Selected for Next Round'.
    2. If Eligible: False: 'Application Status Update' (Not Selected).
    3. Keep body short (max 3-4 sentences).
    4. Extract candidate email from resume.
                
    Output Email Format:
    To: [Candidate Email]
    Subject: [Status Subject]
    Body:
    [Concise Body]

    Job Description:
    {jd}

    Resume:
    {resume_text}
    """
    
    try:
        res = llm.call(evaluate_prompt)
        
        evaluation_str = res
        email_str = ""
        
        if "--- EVALUATION DONE ---" in res:
             parts = res.split("--- EVALUATION DONE ---")
             evaluation_str = parts[0].strip()
             email_str = parts[1].strip()
        else:
             # Fallback if delimiter missing, look for email tags
             if "To:" in res and "Subject:" in res:
                 parts = res.split("To:")
                 evaluation_str = parts[0].strip()
                 email_str = "To: " + parts[1].strip()
             
        return {
            "evaluation": evaluation_str,
            "email": email_str
        }
    except Exception as e:
         return {
            "evaluation": f"Error evaluating candidate: {str(e)}",
            "email": ""
         }
