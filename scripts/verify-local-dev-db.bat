@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0database-lifecycle-runner.ps1" -Target local-dev -Action verify
exit /b %ERRORLEVEL%
