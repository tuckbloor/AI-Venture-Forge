@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo [AgentForge] Creating Python environment...
    where py >nul 2>nul
    if not errorlevel 1 (
        py -3.14 -m venv .venv 2>nul
        if errorlevel 1 py -3 -m venv .venv
    ) else (
        python -m venv .venv
    )
    if errorlevel 1 (
        echo [ERROR] Could not create .venv. Install Python 3.11+ from python.org and retry.
        exit /b 1
    )
)
if not exist ".venv\agentforge-installed.txt" (
    echo [AgentForge] Installing Python dependencies first time...
    ".venv\Scripts\python.exe" -m pip install -r requirements-dev.txt
    if errorlevel 1 (
        echo [ERROR] Dependency installation failed. Check your internet connection and Python installation.
        exit /b 1
    )
    echo v0.2 > ".venv\agentforge-installed.txt"
)
exit /b 0
