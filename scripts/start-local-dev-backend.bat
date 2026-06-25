@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0local-env-runner.ps1" -Target local-dev -Service backend
exit /b %ERRORLEVEL%
