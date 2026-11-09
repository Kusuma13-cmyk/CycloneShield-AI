@echo off
REM CycloneShield AI — Launch script (Windows CMD)
REM Uses the project .venv (Python 3.13 with ibm-watsonx-ai) on port 8503
REM Usage: run.bat

SET SCRIPT_DIR=%~dp0
SET VENV_PYTHON=%SCRIPT_DIR%.venv\Scripts\python.exe
SET VENV_STREAMLIT=%SCRIPT_DIR%.venv\Scripts\streamlit.exe

IF NOT EXIST "%VENV_PYTHON%" (
    echo ERROR: .venv not found at %VENV_PYTHON%
    echo Run: python -m venv .venv ^&^& .venv\Scripts\pip install -r requirements-local.txt
    pause
    exit /b 1
)

echo [CycloneShield AI] Using interpreter: %VENV_PYTHON%
"%VENV_PYTHON%" -c "import ibm_watsonx_ai; print('[OK] ibm-watsonx-ai', ibm_watsonx_ai.__version__)" 2>NUL || echo [WARN] ibm-watsonx-ai not installed in .venv

echo [CycloneShield AI] Starting on http://localhost:8503
"%VENV_PYTHON%" -m streamlit run app.py --server.port 8503 --server.address localhost
