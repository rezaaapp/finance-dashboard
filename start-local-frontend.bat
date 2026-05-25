@echo off
setlocal

set PORT=5173
set ROOT=%~dp0
set FRONTEND_DIR=%ROOT%frontend

echo Stopping existing frontend process on port %PORT% if any...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr /R /C:":%PORT% .*LISTENING"') do (
  if not "%%a"=="0" (
    taskkill /PID %%a /F >nul 2>nul
  )
)

echo Starting frontend on http://127.0.0.1:%PORT%
cd /d "%FRONTEND_DIR%"
npm.cmd run dev -- --host 127.0.0.1

endlocal
