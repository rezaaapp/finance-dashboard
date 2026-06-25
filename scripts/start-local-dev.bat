@echo off
setlocal
pushd "%~dp0.."
start "Omon local-dev backend" cmd /k "scripts\start-local-dev-backend.bat"
start "Omon local-dev frontend" cmd /k "scripts\start-local-dev-frontend.bat"
popd
