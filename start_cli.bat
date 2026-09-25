@echo off
cd /d "%~dp0"
if not exist "%~dp0.venv\Scripts\python.exe" (
    echo No se encontro el Python del entorno virtual: .venv\Scripts\python.exe
    pause
    exit /b 1
)
"%~dp0.venv\Scripts\python.exe" "%~dp0translator.py" --input 14 --output 21 %*
if errorlevel 1 pause
