@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0local-env-runner.ps1" -Target local-prod -Service frontend
exit /b %ERRORLEVEL%
