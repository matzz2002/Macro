@echo off
setlocal

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m PyInstaller --noconfirm --windowed --name MacroForge run_app.py

echo.
echo Gotowy plik EXE znajduje sie w katalogu dist\MacroForge\MacroForge.exe
pause
