@echo off
setlocal
cd /d "%~dp0"
py -m macro_win10 gui
if errorlevel 1 pause
