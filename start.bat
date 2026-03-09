@echo off
echo ==============================================
echo Installing requirements...
echo ==============================================
call conda activate hpr
pip install -r requirements.txt

echo.
echo ==============================================
echo Starting FastAPI Backend...
echo ==============================================
start "FastAPI Backend" cmd /c "call conda activate hpr & uvicorn backend.main:app --reload --port 8000"

echo.
echo ==============================================
echo Starting Streamlit Frontend...
echo ==============================================
start "Streamlit Frontend" cmd /c "call conda activate hpr & streamlit run frontend\app.py"

echo.
echo Both servers are starting in new windows!
echo FastApi Docs: http://localhost:8000/docs
echo Streamlit App: http://localhost:8501
pause
