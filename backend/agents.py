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
        goal="Evaluate a candidate's resume against a Job Description, calculate a matching percentage, and determine explicitly if they are eligible based on a 70% threshold.",
        backstory="You are a strict but fair recruiter. You meticulously compare the skills, experience, and qualifications in the resume against the job description requirements to compute an accurate matching score out of 100.",
        verbose=True,
        allow_delegation=False,
        llm=llm
    )

    scheduler_agent = Agent(
        role="HR Scheduling Coordinator",
        goal="If a candidate is selected (score >= 70%), generate a polite interview scheduling email for them.",
        backstory="You are a friendly HR scheduling coordinator. You write professional emails to invite candidates to the next round of interviews. If a candidate is NOT eligible, you politely inform them of rejection.",
        verbose=True,
        allow_delegation=False,
        llm=llm
    )

    evaluate_task = Task(
        description=f'''
Review the following resume against the provided Job Description.
Calculate a matching score out of 100 based on skills, experience, and qualifications.
If the score is 70 or higher, output 'Eligible: True'. Otherwise, 'Eligible: False'.

Job Description:
{jd}

Resume:
{resume_text}
''',
        expected_output="A summary of the candidate's strengths/weaknesses compared to the JD, a final percentage score (e.g., 'Score: 75%'), and a conclusion of 'Eligible: True' or 'Eligible: False'.",
        agent=reviewer_agent
    )

    schedule_task = Task(
        description="""
Based strictly on the output of the previous evaluation task:
1. If the candidate is marked as Eligible (score >= 70%), write a short, professional interview invitation email proposing a time for a real person to interview them.
2. If they are Not Eligible (score < 70%), output a short, polite rejection email instead.
""",
        expected_output="An email text (either an invitation to interview or a polite rejection).",
        agent=scheduler_agent
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
