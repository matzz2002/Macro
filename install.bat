@echo off
REM One-time setup: install the required Python packages on Windows.

setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 -m pip install --upgrade pip
    py -3 -m pip install -r requirements.txt
) else (
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
)

echo.
echo Done. Run run_gui.bat to start the Macro Recorder.
pause
endlocal
