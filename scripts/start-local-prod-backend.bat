@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0local-env-runner.ps1" -Target local-prod -Service backend
exit /b %ERRORLEVEL%
