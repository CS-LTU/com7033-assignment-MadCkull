@echo off
REM Activate the virtual environment
call .venv\Scripts\activate

REM Run the Python script
python .\stroke_vision\run.py

REM Keep the window open after execution
pause
