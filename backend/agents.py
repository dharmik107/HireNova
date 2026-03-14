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

def generate_jd(prompt: str) -> str:
    """Generates a Job Description from a simple prompt using CrewAI."""
    
    # 1. Perform Static Research to avoid LLM tool loops/exhaustion 
    import wikipedia
    research_context = ""
    try:
        research_context = wikipedia.summary(prompt, sentences=3)
    except Exception:
        try:
            # Fallback for list disambiguations
            search_results = wikipedia.search(prompt, results=3)
            if search_results:
                research_context = wikipedia.summary(search_results[0], sentences=3)
        except Exception:
             research_context = "Standard industry qualifications and standard benchmarks apply."

    researcher_agent = Agent(
        role="Job Role & Industry Analyst",
        goal="Conduct comprehensive technical research on the job role by using contextual research data directly injected.",
        backstory=(
            "You are an expert HR Data Scientist and Market Analyst. You understand the absolute details of any position. "
            "You break down titles into actionable technical requirements by reviewing provided industry benchmarks and core expectations."
        ),
        verbose=True,
        allow_delegation=False,
        llm=llm
    )

    research_task = Task(
        description=f'''
        Analyze the hiring manager's prompt: "{prompt}"
        
        Use this **Provided Internet Research context** to verify details:
        """
        {research_context}
        """

        Based on the Context and your knowledge, research and summarize:
        
        **CRITICAL STEP**: First determine if this is an **Internship/Entry-level** role OR an **Experienced (e.g., 3+ years)** role. **DO NOT MIX BOTH.**

        0. **Domain Classification**: Determine if the role belongs to **IT/Software**, **Sales/BDE**, **HR**, **Marketing**, or **Finance**. Strictly state: `Domain: [Domain Name]` at the top of your response. If the domain is Non-IT, NEVER include software engineering terms or coding frameworks in the research conclusions.

        1. **Core Responsibilities**: 4-5 key tasks standard for this exact role.
           - **If Intern**: Focus on developing features under guidance, bug fixes, and learning.
           - **If Experienced**: Focus on designing scalable architecture, microservices, and system optimization.
        2. **Technical Stack & Tools**: Standard technologies used. (DO NOT assume Node.js/React unless explicitly mentioned in the prompt. Detech topics fitting the prompt's domain e.g., if GenAI, cover LLMs, RAG, Embeddings, Prompt engineering).
        3. **Minimum Requirements**: Common experience levels for the role.
        4. **Duration**: ONLY extract a duration if explicitly mentioned in the prompt (e.g., "6 months"). If not specified, state "Not Specified".
        5. **Learning Outcomes**: If Intern, itemize 3-4 **high-value, career-accelerating skills**. **OMIT THIS ENTIRELY if it is an experienced role.**

        Expected output is a structural breakdown of these points. DO NOT generate the JD yourself. Just provide the research notes.
        ''',
        expected_output="A structured breakdown consisting EXACTLY of either Internship items OR Experienced items, with no mixing of the two.",
        agent=researcher_agent
    )

    jd_agent = Agent(
        role="Senior Executive Recruiter",
        goal="Write a clean, impactful, and perfectly formatted job description that gets straight to the point.",
        backstory=(
            "You are an elite Talent Acquisition Specialist known for your ability to create highly effective, easy-to-read job descriptions. "
            "You avoid buzzwords, corporate fluff, and dense paragraphs. "
            "You focus on structural clarity, ensuring that candidates instantly understand the role, responsibilities, and requirements without reading heavy text blocks."
        ),
        verbose=True,
        allow_delegation=False,
        llm=llm
    )

    jd_task = Task(
        description=f'''
        Create a concise, structured, and professional job description based on the prompt: "{prompt}" AND the Research Notes provided by the Position Analyst.

        STRICT CONSTRAINTS (No Fluff):
        1. Use the Research Notes to ensure exact accuracy of skills and roles.
        2. **Do NOT add ANY preamble or postscript**. Start directly with the layout.
        3. **Deduce Target Seniority & Domain Verbs**: 
           - **If IT/Software Domain**: Use engineering verbs like "build", "architect", "optimize", "develop".
           - **If Non-IT Domain (e.g. Sales/BDE, HR)**: Use business verbs like "support lead generation", "assist with market pitching", "manage onboarding". **NEVER** use words like "develop" or "architect" unless explicitly applicable to business processes.
           - **If Intern**: Phrasing MUST be mentorship-driven (e.g., "assist with", "develop under guidance").
           - **If Experienced (3+ years)**: Phrasing MUST be delivery and leadership driven (e.g., "drive", "own strategic execution", "optimize"). Avoid entry-level action items.

        EXACT LAYOUT INSTRUCTIONS (Follow this structure strictly):
        1. **Job Title**: The exact role title formatted as an H1 heading (e.g. `# GenAI Intern`).
        2. **Company**: Must be formatted exactly as `**Company:** [Company Name]` on a new line.
        3. **Location**: Must be formatted exactly as `**Location:** [Location]` on a new line.
        4. **Duration**: Must be formatted exactly as `**Duration:** [Duration]` on a new line. **CRITICAL: OMIT this line entirely if the Research Notes say "Not Specified".**
        5. **Spacing**: ALWAYS leave a blank line after headings 1-4.
        
        6. **What candidate needs to do**: Use `### What candidate needs to do` as a heading. Then a blank line, then 4-5 bullet points of core tasks tailored strictly to the matched experience level.
        7. **Skills needed in candidate**: Use `### Skills needed in candidate` as a heading. Provide exactly 4-5 bullet points of requirements.
        8. **What you will learn**: Use `### What you will learn` as a heading. **CRITICAL: OMIT this section completely if the role is a full-time, experienced, or permanent position (non-internship).** For internships/training only, list 3-4 high-value learning outcomes.
        9. **How to Apply**: Use `### How to Apply` as a heading. Add brief instructions to submit a resume.

        CRITICAL: Never output large blocks of text. Ensure there is a blank line between every single heading and its content. Do NOT use sections like "About Us" or "The Role". Follow this list strictly.
        ''',
        expected_output="A high-quality, concise Markdown string strictly following the requested structure without unnecessary fluff.",
        context=[research_task],
        agent=jd_agent
    )

    reviewer_agent = Agent(
        role="HR & Technical Auditor",
        goal="Audit and enrich the Job Description string to guarantee extreme accuracy against the Hiring Manager prompt domain.",
        backstory=(
            "You are an expert HR Quality Auditor. You read over generated job descriptions and ensure technical domain keywords are relevant. "
            "If the job is for GenAI, you guarantee it includes keywords like LLMs, RAG, VectorDBs, or prompt engineering where applicable. "
            "You ensure no Node.js or React boilerplate pollutes non-web prompts."
        ),
        verbose=True,
        allow_delegation=False,
        llm=llm
    )

    review_task = Task(
        description=f'''
        Review the Job Description generated by the Senior Recruiter against the Hiring Manager prompt: "{prompt}".
        
        CRITICAL AUDIT:
        1. Does it properly address the domain area? (e.g., ONLY for strictly GenAI/ML roles should you mention LLMs, RAG, or Vector Databases. For traditional back-office roles like HR Architect, use relevant benchmarks like HRIS, Payroll SaaS, compliance metrics, and NEVER force GenAI keywords unless the prompt explicitly mentions AI). If incorrect boilerplate is present, rewrite natural bullet titles organically.
        2. Verify complete adherence to the strict EXACT LAYOUT structure guidelines.
        
        Output the final audit-verified Job Description without preamble.
        ''',
        expected_output="A finalized, polished Markdown Job Description correctly reflecting initial prompt domains without generic boilerplates.",
        context=[jd_task],
        agent=reviewer_agent
    )

    crew = Crew(
        agents=[researcher_agent, jd_agent, reviewer_agent],
        tasks=[research_task, jd_task, review_task]
    )
    
    result = crew.kickoff()
    result_str = result.raw if hasattr(result, 'raw') else str(result)
    
    # Post-processing to enforce strict layout omissions
    import re
    # Remove Duration line if it contains negative placeholders or guessed "Permanent"
    result_str = re.sub(r'\*\*Duration:\*\*\s*(Not Specified|None|N/A|Permanent)\b', '', result_str, flags=re.IGNORECASE)
    
    # Clean Auditor justification noise often appended by 8B models
    if "Rewritten Job Description:" in result_str:
        result_str = result_str.split("Rewritten Job Description:")[-1]
    elif "Audit Notes:" in result_str:
        result_str = result_str.split("Audit Notes:")[0]
        
    return result_str.strip()

def evaluate_candidate(jd: str, resume_text: str) -> dict:
    """Evaluates a resume against a JD and schedules an interview if applicable."""
    
    reviewer_agent = Agent(
        role="Senior Technical Recruiter",
        goal="Conduct a high-caliper, context-aware evaluation of the resume against the JD. Distinguish between Internship/Entry-level and Experienced roles and determine eligibility based on an 80% threshold.",
        backstory="You are an elite, no-nonsense Executive Technical Recruiter. You look beyond keywords to find genuine talent. You are brutally honest but contextually aware—you know that an Intern should be judged on skills and potential, while an SDE with 3 years must be judged on proven professional track record and seniority.",
        verbose=True,
        allow_delegation=False,
        llm=llm
    )

    scheduler_agent = Agent(
        role="HR Scheduling Coordinator",
        goal="If a candidate is selected (score >= 80%), find their email in the resume and generate a professional interview scheduling email.",
        backstory="You are a friendly HR scheduling coordinator. You write professional emails to invite candidates to the next round of interviews. If a candidate is NOT eligible, you politely inform them of rejection.",
        verbose=True,
        allow_delegation=False,
        llm=llm
    )

    evaluate_task = Task(
        description=f'''
        Review the following resume against the provided Job Description with extreme scrutiny. 
        Calculate a matching score out of 100 based on technical skills, professional experience, and alignment.

        CRITICAL INSTRUCTIONS:
        1. **Context-Aware Evaluation**: First, identify if the JD is for an **Internship/Entry-level** role or an **Experienced** role.
        2. **Experience Scoring**: 
           - **For Experienced Roles**: If the JD requires 3+ years and the candidate has <3 years (or 0), deduct points proportionally. 0 experience = NOT ELIGIBLE for experienced roles.
           - **For Internship/Entry-level Roles**: Do NOT penalize for lack of professional years. Rate based on skills, academic projects, and potential.
        3. **Detailed Feedback Sections**: Provide a structured breakdown EXACTLY using these Headers:
           - **Technical Alignment**: How well do they know the specific stack? Comparison of tools.
           - **Role Fit**: Does their level (Intern vs Experienced) match requirements?
           - **Strengths**: 3-4 bullet items of what makes them stand out.
           - **Critical Gaps**: What are they missing? **(CRITICAL: Explicitly specify the direct Reason for Rejection if Score < 75)**.
           - **Final Verdict**: A clear justification of why they are suited or unsuited for the role, concluding strictly with `Eligible: True/False`. **Do NOT output any numerical score or percentage.**

        Job Description:
        {jd}

        Resume:
        {resume_text}
        ''',
        expected_output="A structured report itemizing Technical Alignment, Role Fit, Strengths, Critical Gaps, and a Final Verdict concluding with Score and Eligible Status.",
        agent=reviewer_agent
    )

    schedule_task = Task(
        description=f"""
        Based on the Technical Recruiter's evaluation, draft a short email to the candidate.
        Rules:
        1. If Eligible: True: 'Selected for Next Round'.
        2. If Eligible: False: 'Application Status Update' (Not Selected).
        3. Keep the body extremely short (max 3-4 sentences).
        4. Extract the candidate's email from the resume: {resume_text}
                
        Output Format:
        To: [Candidate Email]
        Subject: [Clear Status Subject]
        Body:
        [Concise Body]
        """,
        context=[evaluate_task],
        agent=scheduler_agent,
        expected_output="A structured email containing To, Subject, and a short 3-sentence Body."
    )

    crew = Crew(
        agents=[reviewer_agent, scheduler_agent],
        tasks=[evaluate_task, schedule_task]
    )
    
    result = crew.kickoff()
    
    # Extract results safely for API response
    evaluation_str = evaluate_task.output.raw if hasattr(evaluate_task, 'output') and hasattr(evaluate_task.output, 'raw') else str(getattr(evaluate_task, 'output', ''))
    email_str = schedule_task.output.raw if hasattr(schedule_task, 'output') and hasattr(schedule_task.output, 'raw') else str(getattr(schedule_task, 'output', ''))
    
    return {
        "evaluation": evaluation_str,
        "email": email_str
    }
