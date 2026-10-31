@echo off
setlocal
cd /d "%~dp0"
call ensure-env.bat
if errorlevel 1 (pause & exit /b 1)
if not exist "data" mkdir "data"
REM No interactive 1/2/3 menu: launch worker and dashboard directly.
REM If restarting after a crash, stop existing AgentForge processes first to avoid duplicates.
start "AgentForge Worker" /min ".venv\Scripts\pythonw.exe" worker_silent.py
start "AgentForge Dashboard" /min ".venv\Scripts\pythonw.exe" -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false --server.headless true
start "" "http://127.0.0.1:8501"
echo AgentForge launched. Use the browser dashboard for all controls.
echo Worker log: data\worker.log
exit /b 0
