# 🏗️ HireNova Architecture 

> **A high-level overview of the HireNova multi-agent ecosystem and data flow.**

This document outlines how the frontend, backend, database, and AI agents interact to automate the recruitment pipeline from Job Creation to Candidate Evaluation.

---

## 🌊 Application Flow Diagram

```mermaid
sequenceDiagram
    participant User as 👤 HR / Recruiter (Streamlit)
    participant FastAPI as 🚀 Backend (FastAPI)
    participant NeonDB as 🗄️ Database (PostgreSQL)
    participant CrewAI as 🧠 CrewAI Orchestrator
    participant Groq as ⚡ LLM (Groq)

    %% Flow 1: Job Generation
    rect rgb(240, 248, 255)
    Note over User, Groq: Flow 1: Job Description Generation
    User->>FastAPI: POST /generate_jd (Simple Prompt)
    FastAPI->>CrewAI: Trigger "Senior Recruiter" Agent
    CrewAI->>Groq: Generate formatted Markdown JD
    Groq-->>CrewAI: Return pristine JD text
    CrewAI-->>FastAPI: 
    FastAPI->>FastAPI: Extract Job Title
    FastAPI->>NeonDB: Save [Title, Content]
    FastAPI-->>User: Display Generated JD
    end

    %% Flow 2: Candidate Evaluation
    rect rgb(245, 255, 245)
    Note over User, Groq: Flow 2: Resume Evaluation
    User->>FastAPI: GET /jds
    FastAPI->>NeonDB: Fetch Saved Jobs
    NeonDB-->>FastAPI: Return Job List
    FastAPI-->>User: Populate GUI Dropdown
    User->>FastAPI: POST /evaluate_resume (Selected JD + CV PDF/DOCX)
    FastAPI->>FastAPI: Parse Text (PyPDF2 or python-docx)
    FastAPI->>CrewAI: Trigger "Senior Recruiter" & "Coordinator" Agents
    CrewAI->>Groq: Analyze Resume vs JD + Draft Email
    Groq-->>CrewAI: Return Evaluation & Email Draft
    CrewAI-->>FastAPI: Return final JSON structure
    FastAPI-->>User: Render Scores & Email Draft side-by-side
    end
```

---

## 🏛️ Component Breakdown

The system is separated into three distinct layers to ensure modularity and scalability:

### 1. The Presentation Layer (`frontend/app.py`)
Built entirely in **Streamlit**, this layer provides a highly responsive UI. It directly communicates with the REST API.
* **Sidebar:** Fetches and displays all historically generated Job Descriptions (`GET /jds`) from the backend, providing persistent context. It also handles deletion requests.
* **Step 1 View:** A clean input area for prompt-based Job Description generation.
* **Step 2 View:** A dual-upload interface that pairs a selected database JD with a candidate's uploaded `.pdf` or `.docx` resume. Outputs the final analysis side-by-side using custom HTML/CSS cards.

### 2. The Logic & API Layer (`backend/main.py` & `backend/agents.py`)
Built in **FastAPI**, this is the core orchestrator of the application.
* **File Parsing:** Natively handles the extraction of raw text streams from incoming PDF and DOCX files.
* **Regex Extraction:** Intelligently parses Markdown outputs from the LLM to locate and extract the "Job Title" dynamically.
* **Agent Orchestration (`agents.py`):** Uses **CrewAI** to define distinct personas (e.g., "Senior Executive Recruiter") and goals. It maps incoming API inputs into structured Tasks and delegates them to the Groq LLM.

### 3. The Persistence Layer (`backend/database.py` & `backend/models.py`)
Manages the application's long-term memory.
* **SQLAlchemy ORM:** Maps Python objects to database rows.
* **NeonDB:** A serverless PostgreSQL database hosted in the cloud. It securely stores every generated Job Description (`id`, `title`, `content`), allowing the system to scale beyond simple in-memory session states.
