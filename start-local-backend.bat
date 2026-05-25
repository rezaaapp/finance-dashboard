@echo off
setlocal

set PORT=8000
set ROOT=%~dp0
set BACKEND_DIR=%ROOT%backend

echo Stopping existing backend process on port %PORT% if any...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr /R /C:":%PORT% .*LISTENING"') do (
  if not "%%a"=="0" (
    taskkill /PID %%a /F >nul 2>nul
  )
)

echo Starting backend on http://127.0.0.1:%PORT%
cd /d "%BACKEND_DIR%"
".\venv\Scripts\python.exe" -m uvicorn app.main:app --reload

endlocal
