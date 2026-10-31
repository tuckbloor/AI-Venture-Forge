@echo off
cd /d "%~dp0"
call ensure-env.bat
if errorlevel 1 (pause & exit /b 1)
echo [AgentForge] Background worker is starting. Keep this window open.
".venv\Scripts\python.exe" worker.py --poll-seconds 20
if errorlevel 1 pause
