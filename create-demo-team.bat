@echo off
cd /d "%~dp0"
call ensure-env.bat
if errorlevel 1 (pause & exit /b 1)
".venv\Scripts\python.exe" seed_demo.py
pause
