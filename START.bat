@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title AI Venture Forge
set "ACTION=start"
set "FLAG="
if /I "%~1"=="--stop" set "ACTION=stop"
if /I "%~1"=="--status" set "ACTION=status"
if /I "%~1"=="--disable-autostart" set "ACTION=remove-startup"
if /I "%~1"=="--background" set "FLAG=--background"
if not exist "%~dp0.venv\Scripts\python.exe" goto :source
"%~dp0.venv\Scripts\python.exe" "%~dp0tools\forge_launcher.py" %ACTION% %FLAG%
set "CODE=%ERRORLEVEL%"
if not "%CODE%"=="0" (
  echo Please review the error above and data\logs\server.log / forge-worker.log.
  if /I not "%~1"=="--background" pause
)
exit /b %CODE%
:source
if not exist "%~dp0tools\forge_install.py" goto :missing
where py >nul 2>nul
if not errorlevel 1 (
  py -3 "%~dp0tools\forge_install.py" --launch-installed --action %ACTION%
  goto :source_result
)
where python >nul 2>nul
if errorlevel 1 goto :missing
python "%~dp0tools\forge_install.py" --launch-installed --action %ACTION%
:source_result
set "CODE=%ERRORLEVEL%"
if not "%CODE%"=="0" pause
exit /b %CODE%
:missing
echo AI Venture Forge is not installed in this folder. Run INSTALL.bat first.
pause
exit /b 1
