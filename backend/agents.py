import os
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, LLM

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
    jd_agent = Agent(
        role="Senior Executive Recruiter & Employer Branding Specialist",
        goal="Write an exceptionally high-quality, deeply engaging, and highly professional job description that sounds like it belongs to a top-tier tech company.",
        backstory=(
            "You are an elite Head of Talent Acquisition with 20 years of experience shaping the Employer Brand for Fortune 500 companies and cutting-edge startups. "
            "You never write 'simple' or generic descriptions. Instead, you write comprehensive, beautifully formatted, and deeply engaging descriptions that attract elite talent. "
            "You excel at inferring the nuanced requirements of a role even from a very short prompt, expanding on technical stacks, cultural fit, and real-world responsibilities."
        ),
        verbose=True,
        allow_delegation=False,
        llm=llm
    )

    jd_task = Task(
        description=f'''
        Create a high-quality but concise professional job description based on the following hiring manager's prompt: "{prompt}"

        Your output MUST be robust but brief, avoiding bloated text. 

        STRICT FORMATTING INSTRUCTIONS (Keep sections short and visually separated):
        1. **Job Title**: The exact role title formatted as an H1 heading (e.g. `# GenAI Intern`).
        2. **Company**: Must be formatted exactly as `**Company:** [Company Name]` on a new line.
        3. **Location**: Must be formatted exactly as `**Location:** [Location]` on a new line.
        4. **Spacing**: ALWAYS leave a blank line after Company and Location.
        5. **About Us**: Use `### About Us` as a heading. Then a blank line, then a 1-paragraph summary.
        6. **The Role**: Use `### The Role` as a heading. Then a blank line, then a 1-paragraph summary.
        7. **Key Responsibilities**: Use `### Key Responsibilities` as a heading. Provide exactly 4-5 tasks using actual markdown bullet points (`- `) on separate lines.
        8. **Requirements**: Use `### Requirements` as a heading. Provide exactly 4-5 skills using actual markdown bullet points (`- `) on separate lines.
        9. **Benefits**: Use `### Benefits` as a heading. List 3-4 top perks using actual markdown bullet points (`- `) on separate lines.
        10. **How to Apply**: Use `### How to Apply` as a heading. Add a brief instruction for the candidate to submit their resume, followed by a realistic looking email address (e.g. `careers@[company].com`).

        CRITICAL: Never output large blocks of text. Ensure there is a blank line between every single heading and its content, and between every section. Do NOT use headings for Company and Location.
        ''',
        expected_output="A high-quality, concise Markdown string strictly following the requested structure without unnecessary fluff.",
        agent=jd_agent
    )

    crew = Crew(
        agents=[jd_agent],
        tasks=[jd_task]
    )
    
    result = crew.kickoff()
    return result.raw if hasattr(result, 'raw') else str(result)

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
        goal="If a candidate is selected (score >= 80%), find their email in the resume and generate a professional interview scheduling email with a clear subject line.",
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
1. **Context-Aware Evaluation**: First, identify if the JD is for an **Internship/Entry-level** role or an **Experienced** role (e.g., SDE with 3+ years).
2. **Experience Scoring**: 
   - **For Experienced Roles**: If the JD requires 3+ years and the candidate has <3 years (or 0), deduct 40 points immediately. 0 experience = NOT ELIGIBLE for experienced roles.
   - **For Internship/Entry-level Roles**: Do NOT penalize for lack of professional years. Instead, evaluate based on technical skills, academic projects, GitHub contributions, and potential.
3. **Detailed Feedback**: Provide a structured breakdown including:
   - **Technical Alignment**: How well do they know the specific stack?
   - **Role Fit**: Does their level (Intern vs Experienced) match the JD requirements?
   - **Strengths**: What makes them stand out?
   - **Critical Gaps & Weaknesses**: What are they missing? What are the risks?
   - **Final Verdict**: A clear justification of why they meet or fail the 80% threshold, explicitly considering the role's seniority level.

If the score is 80 or higher, output 'Eligible: True'. Otherwise, 'Eligible: False'.

Job Description:
{jd}

Resume:
{resume_text}
''',
        expected_output="A structured report comprising: Technical Alignment, Experience Depth, Strengths, Critical Gaps, Final Verdict, a Score out of 100 (e.g., 'Score: 85%'), and 'Eligible: True/False'.",
        agent=reviewer_agent
    )

    schedule_task = Task(
        description=f"""
Based on the Technical Recruiter's evaluation, draft a short email to the candidate.
                
Rules:
1. If Score >= 80: 'Selected for Next Round'.
2. If Score < 80: 'Application Status Update' (Not Selected).
3. Keep the body extremely short (max 3-4 sentences).
4. State clearly if they are selected or not.
5. Provide exactly ONE brief reason for the decision.
6. Extract the candidate's email from the resume: {resume_text}
                
Job Context: {jd}
                
Output Format:
To: [Candidate Email]
Subject: [Clear Status Subject]
Body:
[Concise Body]
""",
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
