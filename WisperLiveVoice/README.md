# WisperLiveVoice

Traduce voz al inglés con Whisper `large-v3` en una GPU NVIDIA y reproduce la traducción con ElevenLabs. Para Teams, la salida puede dirigirse a VB-CABLE.

**[Guía completa de instalación y uso](INSTALACION.md)**: requisitos de Windows y CUDA, instalación de Python, variable de entorno `ELEVENLABS_API_KEY`, elección de voz y dispositivos, lanzadores, prueba en Teams y solución de problemas.

Inicio rápido desde la raíz del repositorio, después de seguir la guía:

```powershell
.\start_wisper_gui.bat
```

Para la versión de consola, reemplaza los índices y el ID de voz por los tuyos:

```powershell
.\start_wisper_cli.bat --input 14 --output 21 --voice-id cEIu6qe1v5XA6Xvj3g1D
```

La única variable de entorno de esta versión es `ELEVENLABS_API_KEY`. La voz se pasa como parámetro o se elige en la ventana. Whisper se ejecuta siempre en GPU; el audio de entrada se procesa localmente y solo el texto traducido se envía a ElevenLabs.
