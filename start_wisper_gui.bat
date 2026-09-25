@echo off
setlocal
set "ROOT=%~dp0"
set "PYTHON=%ROOT%.venv\Scripts\python.exe"
if not exist "%PYTHON%" (
    echo No se encontro el Python del entorno virtual: .venv\Scripts\python.exe
    echo Instala las dependencias con: py -m venv .venv ^& .venv\Scripts\python.exe -m pip install -r WisperLiveVoice\requirements.txt
    pause
    exit /b 1
)
"%PYTHON%" "%ROOT%WisperLiveVoice\live_voice_gui.py" --voice-id cEIu6qe1v5XA6Xvj3g1D %*
if errorlevel 1 pause
