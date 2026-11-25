@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0preparar.ps1" -Accion iniciar
if errorlevel 1 pause
