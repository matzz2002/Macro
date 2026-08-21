@echo off
REM Launch the Macro Recorder GUI on Windows.
REM Requires Python 3.8+ and the dependencies from requirements.txt.

setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 run_gui.py
) else (
    python run_gui.py
)

endlocal
