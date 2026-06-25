@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0local-env-runner.ps1" -Target local-dev -Service frontend
exit /b %ERRORLEVEL%
