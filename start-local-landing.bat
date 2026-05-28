@echo off
setlocal

set PORT=5174
set ROOT=%~dp0
set LANDING_DIR=%ROOT%apps\landing

echo Stopping existing landing process on port %PORT% if any...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr /R /C:":%PORT% .*LISTENING"') do (
  if not "%%a"=="0" (
    taskkill /PID %%a /F >nul 2>nul
  )
)

echo Starting landing page on http://127.0.0.1:%PORT%
cd /d "%LANDING_DIR%"
npm.cmd run dev -- --host 127.0.0.1 --port %PORT%

endlocal
