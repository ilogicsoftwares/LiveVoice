# WisperLiveVoice

Traduce voz del micrófono al inglés con Whisper local y reproduce la traducción con ElevenLabs en una salida de audio, por ejemplo **CABLE Input** de VB-CABLE para usar **CABLE Output** como micrófono de Teams.

Usa `large-v3` por defecto para priorizar la precisión de traducción. Whisper traduce voz de otros idiomas **al inglés**; esta implementación no ofrece otros idiomas de destino. Procesa frases al detectar una pausa de aproximadamente 600 ms, por lo que la salida tiene cierta demora y no es una traducción simultánea palabra por palabra.

## Instalación (Windows, PowerShell)

```powershell
cd E:\repositories\LiveVoice
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r WisperLiveVoice\requirements.txt
$env:ELEVENLABS_API_KEY = "TU_TOKEN"
.\.venv\Scripts\python.exe WisperLiveVoice\live_voice.py --list-devices
start_wisper_cli.bat
```

Desde la raíz también puedes iniciar la ventana con `start_wisper_gui.bat`. Ambos lanzadores usan por defecto la voz `cEIu6qe1v5XA6Xvj3g1D`; el de consola usa entrada 14 y salida 21. Puedes reemplazar estos valores pasando las opciones normales después del `.bat`, por ejemplo `start_wisper_cli.bat --input 1 --output 8 --voice-id OTRA_VOZ`. En la ventana, la voz y los dispositivos se pueden cambiar antes de iniciar.

Para ver la transcripción original y la traducción en dos paneles, abre la interfaz gráfica:

```powershell
python live_voice_gui.py --voice-id cEIu6qe1v5XA6Xvj3g1D
```

`--voice-id` es un parámetro obligatorio; no se guarda en las variables de entorno. El único secreto requerido es `ELEVENLABS_API_KEY`. Selecciona tu micrófono físico con `--input` y el dispositivo de reproducción **CABLE Input** con `--output`. En Teams selecciona **CABLE Output** como micrófono. Los índices pueden cambiar, así que consulta `--list-devices` antes de ejecutar. Detén la aplicación con `Ctrl+C`.

La primera ejecución descarga el modelo Whisper. `large-v3` necesita varios GB de memoria. Whisper se carga **siempre en una GPU NVIDIA mediante CUDA**, con cálculo `float16`; si CUDA no está disponible, el programa muestra un error y no usa CPU. Para cambiar el equilibrio entre precisión y velocidad: `--whisper-model medium` o `--whisper-model small`. La voz de entrada se supone en español; `--source-language` acepta otro código de idioma Whisper, como `fr`.

Ejemplo en este equipo (RTX 4060 Ti):

```powershell
python live_voice.py --input 14 --output 21 --voice-id cEIu6qe1v5XA6Xvj3g1D
```

La salida de ElevenLabs usa el modelo `eleven_flash_v2_5` y audio PCM mono a 24 kHz por WebSocket. La aplicación valida que ambos dispositivos acepten 16 kHz de entrada y 24 kHz de salida. El audio capturado se procesa localmente con Whisper; solo el texto traducido se envía a ElevenLabs.

La consola muestra cada segundo el nivel del micrófono y el umbral de detección. También informa cuando captura una frase, cuando Whisper la traduce y cuando ElevenLabs entrega audio. El umbral predeterminado es `0.004`. Si el nivel al hablar no lo alcanza, prueba `--mic-threshold 0.002` (o cambia **Sensibilidad** en la ventana) y verifica que `--input` señale tu micrófono físico. Un umbral más bajo aumenta la sensibilidad y puede captar ruido ambiental.

Por cada frase, la consola muestra `EN:` para la traducción que se envía a ElevenLabs y `ES:` para la transcripción original (o el código indicado en `--source-language`). La voz de ElevenLabs empieza a generarse mientras Whisper hace la segunda pasada para mostrar el original. Esta segunda pasada puede demorar la traducción de frases posteriores. No se vuelve a transcribir el audio de ElevenLabs, porque otra inferencia en GPU aumentaría el riesgo de latencia; la consola confirma cuándo llega y cuántos segundos de audio entrega.

Documentación: [Whisper](https://github.com/openai/whisper), [faster-whisper](https://github.com/SYSTRAN/faster-whisper) y [WebSocket TTS de ElevenLabs](https://elevenlabs.io/docs/eleven-api/guides/how-to/websockets/realtime-tts).
