# Django ElimuVISE Quick Start Script (PowerShell)

Write-Host ""
Write-Host "============================================================"
Write-Host "Django ElimuVISE - Quick Start Setup"
Write-Host "============================================================"
Write-Host ""

# Check if Python is available
$pyCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pyCmd) {
    Write-Host "❌ ERROR: Python is not installed or not in PATH"
    Write-Host "Install Python (3.8+) and re-run this script."
    exit 1
}
$pythonVersion = (& python --version) 2>&1
Write-Host "✓ Python found: $pythonVersion"

# Ensure virtual environment exists and install dependencies
Write-Host ""
Write-Host "[1/4] Preparing virtual environment and installing dependencies..."
if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "- .venv not found. Creating virtual environment..."
    & python -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ ERROR: Failed to create virtual environment"
        exit 1
    }
}
$venvPythonPath = ".\\.venv\\Scripts\\python.exe"
$venvPipPath = ".\\.venv\\Scripts\\pip.exe"
& "$venvPipPath" install -q -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ ERROR: Failed to install dependencies via venv pip"
    Write-Host "Try running: .\.venv\Scripts\python -m pip install -r requirements.txt"
    exit 1
}
Write-Host "✓ Dependencies installed"

# Setup PostgreSQL
Write-Host ""
Write-Host "[2/4] Setting up PostgreSQL database..."
$proc = Start-Process -FilePath $venvPythonPath -ArgumentList 'setup_postgres.py' -NoNewWindow -Wait -PassThru
if ($proc.ExitCode -ne 0) {
    Write-Host "❌ WARNING: Database setup may have failed"
    Write-Host "Try running: .\\venv\\Scripts\\python setup_postgres.py"
}

# Seed sample logins
Write-Host ""
Write-Host "[3/4] Seeding sample logins..."
Write-Host "Populating the database with default test accounts..."
Write-Host ""
$proc = Start-Process -FilePath $venvPythonPath -ArgumentList 'manage.py','seed_db' -NoNewWindow -Wait -PassThru
if ($proc.ExitCode -ne 0) {
    Write-Host "⚠ WARNING: Database seeding failed"
}

# Start server
Write-Host ""
Write-Host "============================================================"
Write-Host "[4/4] Starting Django Development Server"
Write-Host "============================================================"
Write-Host ""
Write-Host "Server starting at: http://127.0.0.1:8000/"
Write-Host "Admin panel at: http://127.0.0.1:8000/admin/"
Write-Host ""
Write-Host "Press Ctrl+C to stop the server"
Write-Host ""

Start-Process "http://127.0.0.1:8000/"
Start-Process -FilePath $venvPythonPath -ArgumentList 'manage.py','runserver' -NoNewWindow
