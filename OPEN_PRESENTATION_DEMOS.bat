@echo off
setlocal
title ATU Presentation Demos
pushd "%~dp0"
if errorlevel 1 exit /b 1
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" "scripts\open_presentation_demos.py" %*
) else (
    python "scripts\open_presentation_demos.py" %*
)
set "DEMO_EXIT=%ERRORLEVEL%"
if not "%DEMO_EXIT%"=="0" pause
popd
exit /b %DEMO_EXIT%
