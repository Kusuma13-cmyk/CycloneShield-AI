# CycloneShield AI — Launch script (PowerShell)
# Uses the project .venv (Python 3.13 with ibm-watsonx-ai) on port 8503
# Usage: .\run.ps1

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPython = Join-Path $ScriptDir ".venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Error "ERROR: .venv not found at $VenvPython"
    Write-Host "Run: python -m venv .venv; .\.venv\Scripts\pip install -r requirements-local.txt"
    exit 1
}

Write-Host "[CycloneShield AI] Using interpreter: $VenvPython" -ForegroundColor Cyan

# Verify SDK
$sdkCheck = & $VenvPython -c "import ibm_watsonx_ai; print('ibm-watsonx-ai', ibm_watsonx_ai.__version__)" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] $sdkCheck" -ForegroundColor Green
} else {
    Write-Warning "[WARN] ibm-watsonx-ai not installed in .venv — run: .\.venv\Scripts\pip install -r requirements-local.txt"
}

Write-Host "[CycloneShield AI] Starting on http://localhost:8503" -ForegroundColor Green
& $VenvPython -m streamlit run app.py --server.port 8503 --server.address localhost
