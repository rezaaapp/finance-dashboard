@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0database-lifecycle-runner.ps1" -Target local-dev -Action reset
exit /b %ERRORLEVEL%
