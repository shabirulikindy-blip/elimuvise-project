@echo off
REM Django ElimuVISE Quick Start Script

echo.
echo ============================================================
echo Django ElimuVISE - Quick Start
echo ============================================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Install Python 3.8+ and re-run this script.
    pause
    exit /b 1
)

echo [1/4] Preparing virtual environment and installing dependencies...
if not exist ".venv\Scripts\python.exe" (
    echo - .venv not found. Creating virtual environment...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
)
echo Installing dependencies via .venv pip...
call .venv\Scripts\python -m pip install -q -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: Failed to install dependencies via venv pip
    echo Try: .venv\Scripts\python -m pip install -r requirements.txt
    pause
    exit /b 1
)
echo ✓ Dependencies installed

echo.
echo [2/4] Setting up PostgreSQL database...
echo Please enter your PostgreSQL credentials when prompted.
call .venv\Scripts\python setup_postgres.py
if %errorlevel% neq 0 (
    echo WARNING: Database setup may have failed
    echo You can try running: .venv\Scripts\python setup_postgres.py
)

echo.
echo [3/4] Seeding sample logins...
call .venv\Scripts\python manage.py seed_db
if %errorlevel% neq 0 (
    echo WARNING: Database seeding failed
)

echo.
echo ============================================================
echo [4/4] Starting Django Development Server
echo ============================================================
echo.
echo Server starting at: http://127.0.0.1:8000/
echo Admin panel at: http://127.0.0.1:8000/admin/
echo.
echo Press Ctrl+C to stop the server
echo.

start http://127.0.0.1:8000/
call .venv\Scripts\python manage.py runserver

pause
