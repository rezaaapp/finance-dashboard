@echo off
setlocal
pushd "%~dp0.."
start "Omon local-prod backend" cmd /k "scripts\start-local-prod-backend.bat"
start "Omon local-prod frontend" cmd /k "scripts\start-local-prod-frontend.bat"
popd
