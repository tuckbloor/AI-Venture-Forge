@echo off
cd /d "%~dp0"
call ensure-env.bat
if errorlevel 1 (pause & exit /b 1)
echo [AgentForge] Open http://127.0.0.1:8501 in your browser
echo [AgentForge] Close the terminal or press Ctrl+C to stop.
".venv\Scripts\python.exe" -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false
if errorlevel 1 pause
