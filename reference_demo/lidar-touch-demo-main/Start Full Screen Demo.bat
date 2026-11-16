@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0launch-demo.ps1" -FullScreen
if errorlevel 1 pause
