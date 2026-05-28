@echo off
setlocal

set ROOT=%~dp0

start "Finance Dashboard Backend" cmd /k ""%ROOT%start-local-backend.bat""
timeout /t 4 /nobreak >nul
start "Finance Dashboard Frontend" cmd /k ""%ROOT%start-local-frontend.bat""

echo Local development servers are starting.
echo Backend:  http://127.0.0.1:8000/api/health
echo Frontend: http://127.0.0.1:5173
echo Landing:  run start-local-landing.bat for http://127.0.0.1:5174

endlocal
