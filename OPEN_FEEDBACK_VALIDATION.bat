@echo off
setlocal
title ATU Measured V2-V3 Comparison
pushd "%~dp0"
if errorlevel 1 exit /b 1
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" "scripts\open_presentation_demos.py" --feedback-validation %*
) else (
    python "scripts\open_presentation_demos.py" --feedback-validation %*
)
set "FEEDBACK_EXIT=%ERRORLEVEL%"
if not "%FEEDBACK_EXIT%"=="0" pause
popd
exit /b %FEEDBACK_EXIT%
