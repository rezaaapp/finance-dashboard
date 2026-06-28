@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0verify-concurrent-local.ps1" %*
exit /b %ERRORLEVEL%
