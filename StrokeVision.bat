@echo off

REM Check if .venv exists
if not exist .venv (
    echo [System] Virtual environment not found. Checking Python version...
    
    REM Capture Python version
    for /f "tokens=2" %%I in ('python --version 2^>^&1') do set pyver=%%I
    
    REM Check if version is explicitly 3.11.0
    if "%pyver%" NEQ "3.11.0" (
        echo [WARNING] Recommended Python version is 3.11.0. You are using %pyver%.
        echo [System] Creating virtual environment with %pyver%...
    ) else (
        echo [System] Python 3.11.0 verified. Creating virtual environment...
    )
    
    python -m venv .venv
    
    if errorlevel 1 (
        echo [Error] Failed to create virtual environment.
        pause
        exit /b
    )
    echo [System] Virtual environment created successfully.
)

REM Activate the virtual environment
call .venv\Scripts\activate

REM Check if requirements are met
python check_requirements.py
if %ERRORLEVEL% NEQ 0 (
    echo [System] Installing/Updating dependencies...
    pip install -r requirements.txt
) else (
    echo [System] Dependencies met. Starting Server...
)

REM Run the Python script
python .\stroke_vision\run.py

REM Keep the window open after execution
pause
