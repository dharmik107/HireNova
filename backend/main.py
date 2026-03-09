from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from backend.models import JobPromptRequest, JDResponse, JobDescription
from backend.database import engine, Base, get_db
from backend.agents import generate_jd, evaluate_candidate
import PyPDF2
import io
import re

# Auto-create tables (if they don't exist)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Automated Hiring API")

# Allow CORS for local testing from Streamlit
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Automated Hiring API is running."}

@app.post("/generate_jd", response_model=JDResponse)
async def api_generate_jd(request: JobPromptRequest, db: Session = Depends(get_db)):
    try:
        jd_content = generate_jd(request.prompt)
        
        # Try to extract the title by looking for "**Job Title**:" or similar heading structures
        title = "Generated Job Description"
        
        # Method 1: Look for explicit "**Job Title**: [Role]"
        title_match_1 = re.search(r'\*\*(?:Job Title|Title)\*\*\s*:\s*(.+)', jd_content, re.IGNORECASE)
        
        # Method 2: Look for the first Level 1 or Level 2 markdown heading
        title_match_2 = re.search(r'^(?:#|##)\s+(.+)', jd_content, re.MULTILINE)
        
        if title_match_1:
            title = title_match_1.group(1).strip()
        elif title_match_2:
            title = title_match_2.group(1).strip()
        else:
            # Method 3: Fallback simply take the first non-empty line
            first_line = jd_content.strip().split("\n")[0]
            if len(first_line) > 3:
                 title = first_line

        # Remove any lingering markdown characters (*, #)
        title = title.replace("*", "").replace("#", "").strip()

        # Save to DB
        new_jd = JobDescription(title=title, content=jd_content)
        db.add(new_jd)
        db.commit()
        db.refresh(new_jd)

        return new_jd
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/jds")
def get_jds(db: Session = Depends(get_db)):
    try:
        jds = db.query(JobDescription).order_by(JobDescription.id.desc()).all()
        return jds
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/jds/{jd_id}")
def delete_jd(jd_id: int, db: Session = Depends(get_db)):
    try:
        jd = db.query(JobDescription).filter(JobDescription.id == jd_id).first()
        if not jd:
            raise HTTPException(status_code=404, detail="JD not found")
        db.delete(jd)
        db.commit()
        return {"status": "success", "message": "JD deleted successfully"}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/evaluate_resume")
async def api_evaluate_resume(
    job_description: str = Form(...),
    file: UploadFile = File(...)
):
    try:
        filename = file.filename.lower()
        if not (filename.endswith('.pdf') or filename.endswith('.docx')):
            raise HTTPException(status_code=400, detail="Only PDF or DOCX files are supported.")
        
        # Read the uploaded file bytes
        file_bytes = await file.read()
        resume_text = ""
        
        if filename.endswith('.pdf'):
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
            for page in pdf_reader.pages:
                text = page.extract_text()
                if text:
                    resume_text += text + "\n"
        
        elif filename.endswith('.docx'):
            # Import docx inline so it doesn't break if not installed correctly right away
            import docx
            doc = docx.Document(io.BytesIO(file_bytes))
            for paragraph in doc.paragraphs:
                if paragraph.text:
                    resume_text += paragraph.text + "\n"
        
        if not resume_text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from the document. It might be scanned or empty.")
        
        # Run CrewAI evaluation
        result = evaluate_candidate(jd=job_description, resume_text=resume_text)
        
        return {"status": "success", "result": result}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
