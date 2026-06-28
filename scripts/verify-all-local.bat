@echo off
setlocal

echo Verifying local-dev database connection...
call "%~dp0verify-local-dev-connection.bat"
if errorlevel 1 (
  echo local-dev verification FAILED. local-prod was not attempted.
  exit /b 1
)

echo Verifying local-prod database connection...
call "%~dp0verify-local-prod-connection.bat"
if errorlevel 1 (
  echo local-prod verification FAILED.
  exit /b 1
)

echo All local database environments PASS.
exit /b 0
