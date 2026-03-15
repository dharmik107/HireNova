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

from pydantic import BaseModel

class SaveJDRequest(BaseModel):
    title: str
    content: str

@app.post("/generate_jd")
async def api_generate_jd(request: JobPromptRequest):
    try:
        jd_content = generate_jd(request.prompt, domain=request.domain, seniority=request.seniority)
        
        # Strip markdown code blocks if the LLM wrapped it
        jd_clean = jd_content.strip()
        if jd_clean.startswith("```markdown"):
            jd_clean = jd_clean[11:].strip()
        elif jd_clean.startswith("```"):
            jd_clean = jd_clean[3:].strip()
        if jd_clean.endswith("```"):
            jd_clean = jd_clean[:-3].strip()
        
        jd_content = jd_clean
        
        # Try to extract the title
        title = ""
        title_match_1 = re.search(r'\*\*(?:Job Title|Title)\*\*\s*[:\-]?\s*(.+)', jd_content, re.IGNORECASE)
        title_match_2 = re.search(r'^(?:#|##)\s*(.+)', jd_content, re.MULTILINE)
        
        if title_match_1:
            title = title_match_1.group(1).strip()
        elif title_match_2:
            title = title_match_2.group(1).strip()
            
        title = title.replace("*", "").replace("#", "").strip()

        # Robust fallback for missing or corrupted title tags (e.g. LLM hallucinates giant text)
        if not title or len(title) > 60:
             # Use structured Composite Fallback instead of raw prompt sentences
             s_part = request.seniority.title() if request.seniority and request.seniority.lower() != "auto-detect" else ""
             d_part = request.domain.title() if request.domain and request.domain.lower() != "auto-detect" else "Job Description"
             title = f"{s_part} {d_part}".strip()
                  
        if not title:
             title = "Generated Job Description"

        # Return dict only, DO NOT auto-save to DB
        return {"title": title, "content": jd_content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/save_jd", response_model=JDResponse)
def save_jd(request: SaveJDRequest, db: Session = Depends(get_db)):
    try:
        new_jd = JobDescription(title=request.title, content=request.content)
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
