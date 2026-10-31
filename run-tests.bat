@echo off
cd /d "%~dp0"
call ensure-env.bat
if errorlevel 1 (pause & exit /b 1)
".venv\Scripts\python.exe" -m pytest -q tests
if errorlevel 1 (echo [ERROR] Tests failed. & pause & exit /b 1)
echo All tests passed.
pause
