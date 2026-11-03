@echo off
setlocal
title ATU Studio Dashboard
color 0B

echo ======================================================================
echo                         ATU Studio Dashboard
echo ======================================================================
echo.
echo Starting the dashboard, or opening it if it is already running...
echo.

pushd "%~dp0"
if errorlevel 1 exit /b 1
if exist "%~dp0.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

"%PYTHON_EXE%" -u "%~dp0serve_frontend.py" %*
set "DASHBOARD_EXIT=%ERRORLEVEL%"
popd

if not "%DASHBOARD_EXIT%"=="0" (
    echo.
    echo [ERROR] The dashboard could not start. See the reason above.
    if not "%~1"=="--no-browser" pause
)
exit /b %DASHBOARD_EXIT%
