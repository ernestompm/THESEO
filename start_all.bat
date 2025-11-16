@echo off
title ODF Graphics App Launcher

echo Starting all services for the ODF Graphics App...
echo Each service will open in a new terminal window.
echo.
echo Note: For the frontend, please run 'npm install' manually in the
echo 'frontend_operator' folder if you haven't already.
echo.

REM Set the base directory to the location of this script
set "BASE_DIR=%~dp0"

REM --- 1. Start Core Backend ---
echo Launching Core Backend...
start "ODF Backend" cmd /k "call "%BASE_DIR%venv\Scripts\activate.bat" && cd /d "%BASE_DIR%core_backend" && uvicorn app.main:app --host 0.0.0.0 --port 8000"

REM Give Windows a moment to process
timeout /t 3 /nobreak > nul

REM --- 2. Start Frontend Operator ---
echo Launching Frontend Operator...
start "ODF Frontend" cmd /k "cd /d "%BASE_DIR%frontend_operator" && npm run dev"

REM Give Windows a moment
timeout /t 3 /nobreak > nul

REM --- 3. Start Ingest Service ---
echo Launching Ingest Service...
start "ODF Ingest Service" cmd /k "call "%BASE_DIR%venv\Scripts\activate.bat" && python "%BASE_DIR%ingest_service\ingest.py""

echo.
echo All services have been launched.
