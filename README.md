# 🚀 HireNova
> **Discover elite talent at lightspeed.** 

Live Demo : https://hirenova.streamlit.app

[![HireNova Demo](https://img.shields.io/badge/Watch-Project%20Demo-blue?style=for-the-badge&logo=linkedin)](https://www.linkedin.com/posts/dharmik-pansuriya_ai-recruitment-hiringautomation-activity-7436922467119566850-jkQU)

HireNova is an intelligent, automated AI hiring system built to empower HR professionals and Technical Recruiters. Powered by **CrewAI**, **FastAPI**, and **Streamlit**, HireNova uses multi-agent intelligent workflows to effortlessly generate premium Job Descriptions and evaluate inbound Candidate Resumes against those roles.

---

## ✨ Core Features

* **AI Job Description Generator**
  * Give a simple prompt (e.g., *"I need a GenAI intern remote"*), and the 'Senior Executive Recruiter' agent will accurately infer the technical stack and generate a comprehensive, highly-detailed Job Description automatically.
* **Persistent Database Storage**
  * All generated Job Descriptions are safely stored in a local/cloud **NeonDB PostgreSQL Database** using SQLAlchemy. Access your entire catalog of open roles right from the sidebar.
* **Intelligent Candidate Evaluation**
  * Upload candidate resumes in either `.pdf` or `.docx` format. Choose an active Job Description from your database, and let the agents score the candidate, creating an Eligibility Index and drafting an automated HR email response.
* **Premium UI**
  * Modern, lightning-fast Streamlit interface supporting light and dark themes seamlessly.

---

## 🛠️ Tech Stack

* **Frontend**: Streamlit
* **Backend**: FastAPI 
* **Database**: Neon (PostgreSQL), SQLAlchemy
* **AI Orchestration**: CrewAI
* **LLM Provider**: Groq
* **Document Parsing**: PyPDF2, python-docx

---

## 🚀 Quick Setup & Installation

### 1. Prerequisites
Ensure you have Python 3.10+ installed.

### 2. Environment Variables
Create a `.env` file in the root directory and add the following keys:
```env
GROQ_API_KEY=your_groq_api_key
NEON_DB_URL="postgresql://username:password@your-neon-db-url/neondb"
```

### 3. Install Dependencies
Install all required libraries via pip:
```bash
pip install -r requirements.txt
```

### 4. Run the Application
You can instantly spin up both the FastAPI backend server and the Streamlit frontend UI simultaneously using the included batch file:
```bash
start.bat
```
*(The backend will run on `http://127.0.0.1:8000` and the UI will open at `http://localhost:8501`)*

---
*Built to accelerate the future of HR.*
