from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, Text
from backend.database import Base
from typing import Optional

# --- SQLAlchemy DB Models ---
class JobDescription(Base):
    __tablename__ = "job_descriptions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    content = Column(Text)

# --- Pydantic Schemas ---
class JobPromptRequest(BaseModel):
    prompt: str
    domain: Optional[str] = None
    seniority: Optional[str] = None

class JDResponse(BaseModel):
    id: int
    title: str
    content: str

    class Config:
        orm_mode = True  # Allows fastAPI to return SQLAlchemy object as JSON
