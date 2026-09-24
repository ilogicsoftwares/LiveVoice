@echo off
cd /d "%~dp0"
if not exist "%~dp0.venv\Scripts\python.exe" (
    echo No se encontro el Python del entorno virtual: .venv\Scripts\python.exe
    pause
    exit /b 1
)
"%~dp0.venv\Scripts\python.exe" "%~dp0translator_gui.py"
if errorlevel 1 pause
