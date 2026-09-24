@echo off
cd /d "%~dp0"
call "%~dp0.venv\Scripts\activate.bat"
if errorlevel 1 (
    echo No se pudo activar .venv. Verifica que exista la carpeta .venv.
    pause
    exit /b 1
)
echo Entorno virtual activado en: %CD%
cmd /k
