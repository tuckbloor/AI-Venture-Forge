@echo off
cd /d "%~dp0"
call ensure-env.bat
if errorlevel 1 (pause & exit /b 1)
echo [AgentForge] Setup complete. Double-click START-HERE.bat to launch.
pause
