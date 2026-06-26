@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0database-lifecycle-runner.ps1" -Target local-prod -Action reset
exit /b %ERRORLEVEL%
