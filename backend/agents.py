import os
import re
import time
from dotenv import load_dotenv
from crewai import LLM
from duckduckgo_search import DDGS

# Load environment variables
load_dotenv()

# Initialize Groq LLM using OpenAI native provider to avoid litellm dependency
llm = LLM(
    model="openai/llama-3.3-70b-versatile",
    api_key=os.environ.get("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
    temperature=0.0
)

# Second LLM for creative layout variation (JD drafting)
llm_generation = LLM(
    model="openai/llama-3.3-70b-versatile",
    api_key=os.environ.get("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
    temperature=0.4
)

def classify_role(prompt: str) -> dict:
    """
    Classify the role from the raw prompt into a structured profile.
    Returns domain, role_domain, key_skills, tools, and differentiator.
    """
    classification_prompt = f"""
    You are a technical recruiter expert. Analyze this hiring prompt: "{prompt}"

    Extract and return STRICTLY in this exact format (no extra text):

    Domain: <Broad industry e.g. Technology, Finance, Healthcare>
    Seniority: <Intern / Entry-Level / Experienced / Senior / Director>
    Role Title: <Exact role title e.g. "Agentic AI Engineer", "GenAI Intern">
    Role Domain: <Specific sub-domain e.g. "AI Agents & Automation", "Generative AI", "Classical Machine Learning">
    Key Skills: <comma-separated list of 6-8 specific technical skills for THIS role>
    Tools & Frameworks: <comma-separated list of 5-7 specific tools/frameworks for THIS role>
    Differentiator: <1 sentence explaining what makes THIS role unique vs other AI/tech roles>

    IMPORTANT: Be VERY specific. Do NOT give generic AI skills for all roles.
    - "AI/ML" role → scikit-learn, PyTorch, model training, feature engineering, MLflow
    - "GenAI" role → LLMs, RAG, prompt engineering, embeddings, Hugging Face, LangChain
    - "Agentic AI" role → AI agents, tool calling, ReAct, AutoGen, CrewAI, memory management, multi-agent systems
    """

    try:
        res = llm.call(classification_prompt)

        def extract(key):
            match = re.search(rf'{key}:\s*(.+)', res, re.IGNORECASE)
            return match.group(1).strip() if match else ""

        return {
            "domain":        extract("Domain")              or "Technology",
            "seniority":     extract("Seniority")           or "Experienced",
            "role_title":    extract("Role Title")          or prompt,
            "role_domain":   extract("Role Domain")         or "Technology",
            "key_skills":    extract("Key Skills")          or "",
            "tools":         extract("Tools & Frameworks")  or "",
            "differentiator":extract("Differentiator")      or "",
        }
    except Exception:
        return {
            "domain": "Technology", "seniority": "Experienced",
            "role_title": prompt, "role_domain": "Technology",
            "key_skills": "", "tools": "", "differentiator": "",
        }



def search_role_context(role_profile: dict) -> str:
    """
    Run 4 targeted DDG searches using the classified role profile.
    Returns a concatenated research context string.
    """
    role_title   = role_profile["role_title"]
    role_domain  = role_profile["role_domain"]
    tools        = role_profile["tools"]
    seniority    = role_profile["seniority"]

    # Build role-aware, unquoted queries (no exact-phrase quotes)
    queries = [
        f"{role_title} {seniority} job description responsibilities 2025",
        f"{role_title} required skills and tools 2025",
        f"{role_domain} engineer skills frameworks libraries",
        f"difference between {role_domain} and other AI roles responsibilities",  # differentiator query
    ]

    # If tools are known, add a tools-specific query
    if tools:
        first_two_tools = ", ".join(tools.split(",")[:2]).strip()
        queries.append(f"{first_two_tools} use cases in {role_domain} projects")

    research_context = ""
    for q in queries:
        try:
            results = DDGS().text(q, max_results=3)
            if results:
                snippets = [
                    f"Source: {r.get('title', 'Web')}\nSnippet: {r.get('body', '')}"
                    for r in results
                ]
                research_context += f"=== Query: {q} ===\n" + "\n\n".join(snippets) + "\n\n"
            time.sleep(0.8)  # avoid DDG rate limiting
        except Exception:
            pass

    if not research_context.strip():
        research_context = f"Standard industry qualifications apply for a {role_title} role."

    return research_context


def generate_jd(prompt: str, domain: str = None, seniority: str = None) -> str:
    """Generates a Job Description from a simple prompt using CrewAI."""

    # ─────────────────────────────────────────
    # STEP 0: Classify Role into Structured Profile
    # ─────────────────────────────────────────
    role_profile = classify_role(prompt)

    # Allow UI overrides for domain / seniority
    if domain and domain.lower() not in ["auto-detect", "none", ""]:
        role_profile["domain"] = domain
    if seniority and seniority.lower() not in ["auto-detect", "none", ""]:
        role_profile["seniority"] = seniority

    # ─────────────────────────────────────────
    # STEP 1: Web Search with Role-Aware Queries
    # ─────────────────────────────────────────
    research_context = search_role_context(role_profile)

    # ─────────────────────────────────────────
    # STEP 2: Dynamic Layout based on Seniority
    # ─────────────────────────────────────────
    is_intern = "intern" in role_profile["seniority"].lower()

    layout_sections = [
        "**Job Title**: The exact role title formatted as an H1 heading (e.g. `# Role Title`).",
        "**Company**: Must be formatted exactly as `**Company:** [Company Name]` on a new line. **OMIT completely if not specified in prompt.**",
        "**Location & Work Mode**: Must be formatted exactly as `**Location & Work Mode:** [Location] | [Mode]` on a new line. **OMIT completely if not specified.**",
    ]

    if is_intern:
        layout_sections.append("**Duration**: Must be formatted exactly as `**Duration:** [Duration]` on a new line. OMIT if not specified.")
        layout_sections.append("**Stipend**: Must be formatted exactly as `**Stipend:** [Value]` on a new line. OMIT if not specified.")

    layout_sections.extend([
        "**About the Company**: Use `### About the Company` as a heading. Add 1-2 lines detailing the environment.",
        "**Eligibility**: Use `### Eligibility` as a heading. Itemize 1-2 lines on degree/years requirement.",
        "**Key Responsibilities**: Use `### Key Responsibilities` as a heading. Bullet points of core tasks.",
        "**Skills & Tools**: Use `### Skills & Tools` as a heading. Bullet points prioritizing modern frameworks.",
        "**Perks & Benefits**: Use `### 🎁 Perks & Benefits` as a heading. List competitive advantages.",
    ])

    if is_intern:
        layout_sections.append("**What you will learn**: Use `### What you will learn` as a heading.")

    layout_sections.append("**How to Apply**: Use `### How to Apply` as a heading. Add brief instructions.")

    layout_instructions = "- " + "\n- ".join(layout_sections)


    generate_prompt = f"""
    You are an expert technical recruiter. Create a concise, structured, and professional
    job description based on the details below.

    ── ROLE PROFILE (extracted from hiring prompt) ──
    Original Prompt    : "{prompt}"
    Exact Role Title   : {role_profile["role_title"]}
    Broad Domain       : {role_profile["domain"]}
    Specific Sub-Domain: {role_profile["role_domain"]}
    Seniority Level    : {role_profile["seniority"]}
    Key Skills         : {role_profile["key_skills"]}
    Tools & Frameworks : {role_profile["tools"]}
    What makes this role UNIQUE: {role_profile["differentiator"]}

    ── RESEARCH CONTEXT (from web search) ──
    {research_context}

    ── STRICT RULES ──
    1. **Use the Role Profile above as your PRIMARY source of truth.**
       The Key Skills and Tools listed MUST appear in the JD. Do NOT substitute generic skills.

    2. **Role Differentiation is MANDATORY.**
       This JD is for "{role_profile["role_title"]}" in the "{role_profile["role_domain"]}" sub-domain.
       It MUST be clearly different from a generic AI/tech JD. Use the "What makes this role UNIQUE"
       field to write responsibilities and skills that are specific ONLY to this role.

    3. **From Research Context**: Extract bullet points for Skills, Tools, and Responsibilities.
       Only use findings that are relevant to "{role_profile["role_title"]}". Ignore unrelated snippets.

    4. **No Placeholders**: NEVER output square brackets like `[...]` or `[Insert ...]`.
       If any detail (Company, Location, Compensation) is missing, OMIT that line completely.

    5. **Tone**: Highly professional and engaging.

    ── LAYOUT (follow strictly) ──
    {layout_instructions}
    """

    try:
        result_str = llm_generation.call(generate_prompt)
    except Exception as e:
        result_str = f"Error generating JD: {str(e)}"

    # ─────────────────────────────────────────
    # Post-processing (unchanged from original)
    # ─────────────────────────────────────────
    result_str = re.sub(r'(?m)^.*?\[.*?\].*?(?:\n|$)', '', result_str)
    result_str = re.sub(
        r'(?m)^\*?\*?\s*(Duration|Stipend|Company|Location & Work Mode)\s*:?\*?\*?\s*'
        r'(?:Not Specified|None|N/A|Permanent|Unspecified|XYZ Corp|XYZ|To be discussed|Competitive)\b.*?(?:\n|$)',
        '', result_str, flags=re.IGNORECASE
    )

    if "intern" not in role_profile["seniority"].lower():
        result_str = re.sub(
            r'(?m)^\*?\*?\s*(Duration|Stipend|What you will learn)\s*:?\*?\*?.*?(?:\n|$)',
            '', result_str, flags=re.IGNORECASE
        )

    result_str = re.sub(r'\(No.*?(?:specified|omit).*?\)', '', result_str, flags=re.IGNORECASE)

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
            if "To:" in res and "Subject:" in res:
                parts = res.split("To:")
                evaluation_str = parts[0].strip()
                email_str = "To: " + parts[1].strip()

        return {"evaluation": evaluation_str, "email": email_str}

    except Exception as e:
        return {"evaluation": f"Error evaluating candidate: {str(e)}", "email": ""}