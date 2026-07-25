@echo off
echo Starting Fake Productivity Detector Backend...
echo.
cd /d "%~dp0"
.\venv\Scripts\uvicorn.exe app.main:app --reload --port 8000
pause
