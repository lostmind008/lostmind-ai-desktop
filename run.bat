@echo off
REM Run Script for LostMind AI Gemini Chat Assistant
REM This script sets up environment variables and runs the application

echo Starting LostMind AI Gemini Chat Assistant...

REM Check if Python is available
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Error: Python not found. Please install Python 3.9 or newer.
    exit /b 1
)

REM Check for virtual environment
if exist venv\Scripts\activate.bat (
    echo Using virtual environment...
    call venv\Scripts\activate.bat
)

REM Check if requirements are installed
python -c "import PyQt6" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Installing dependencies...
    pip install -r requirements.txt
)

REM Run the application
python run.py %*
