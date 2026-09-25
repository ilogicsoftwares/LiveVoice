# Instalar y usar WisperLiveVoice en Windows

WisperLiveVoice toma audio del micrófono, lo traduce **al inglés** con Whisper `large-v3` en una GPU NVIDIA y envía el texto a ElevenLabs para generar voz. Con VB-CABLE puedes usar esa voz como micrófono de Teams. Hay una ventana con transcripciones y una versión de consola.

Whisper trabaja por frases: espera 600 ms de silencio por defecto para traducir y conserva la frase completa para darle contexto al modelo. Hay un límite de seguridad de 8 s para habla sin pausas. La primera ejecución descarga el modelo y puede tardar más. La voz se reproduce en la salida seleccionada, que puede ser el cable virtual en vez de tus audífonos.

## Instalador de Windows (.exe)

Descarga `WisperLiveVoice-Setup-*-win64.exe` desde el [último release](https://github.com/ilogicsoftwares/LiveVoice/releases/latest), ejecútalo y abre **WisperLiveVoice** desde el menú Inicio. El instalador incluye Python, las dependencias de la aplicación y las bibliotecas CUDA necesarias; **no necesitas crear `.venv` ni instalar CUDA Toolkit** para esta opción. Sí necesitas una GPU NVIDIA con controlador compatible y [VB-CABLE](../README.md#3-install-the-vb-cable-virtual-microphone-on-windows) si vas a enviar la voz a Teams.

Configura la clave de API y, opcionalmente, el ID de voz como variables de usuario de Windows:

```powershell
setx ELEVENLABS_API_KEY "TU_TOKEN_DE_ELEVENLABS"
setx ELEVENLABS_VOICE_ID "TU_VOICE_ID"
```

Abre de nuevo la aplicación después de configurar las variables. En la ventana selecciona tu micrófono físico y la salida; para Teams usa **CABLE Input** como salida y **CABLE Output** como micrófono de Teams. También puedes editar el ID de voz en la ventana. En el primer inicio, Whisper descarga automáticamente `large-v3` (alrededor de 3 GB); requiere Internet y espacio libre. Los pasos numerados siguientes son para ejecutar el proyecto **desde el código fuente**.

## 1. Requisitos

- Windows 10/11 de 64 bits y [Python 3.12 x64](https://www.python.org/downloads/) (versión probada). Instala el lanzador `py` si el instalador lo ofrece.
- GPU NVIDIA con controlador actualizado. Ejecuta `nvidia-smi` en PowerShell para comprobar que Windows la detecta. Esta aplicación **requiere GPU** y usa CUDA con cálculo `float16`; no tiene modo CPU.
- [cuBLAS para CUDA 12 y cuDNN 9 para CUDA 12](https://github.com/SYSTRAN/faster-whisper#gpu) accesibles desde `PATH`. Sigue la [instalación de NVIDIA para Windows](https://docs.nvidia.com/deeplearning/cudnn/installation/latest/backend.html) y abre otra terminal después de cambiar `PATH`. Que `nvidia-smi` funcione no garantiza que estén presentes estas bibliotecas.
- Micrófono, audífonos, Internet y cuenta de [ElevenLabs](https://elevenlabs.io/docs/eleven-api/quickstart) con API key habilitada para Text to Speech. El uso de la API puede generar cargos.
- Para Teams: [VB-CABLE](https://vb-audio.com/Cable/). Sigue los [pasos de instalación y configuración en el README principal](../README.md#3-instalar-el-micrófono-virtual-vb-cable).

No hace falta instalar FFmpeg por separado: `faster-whisper` usa PyAV. Si `large-v3` no cabe en la memoria de tu GPU, puedes elegir `medium` o `small`, con posible pérdida de precisión.

## 2. Obtener el repositorio e instalar las dependencias

Descarga el repositorio como ZIP y extráelo, o clónalo con Git. Abre PowerShell en la **raíz de LiveVoice**, donde están `start_wisper_gui.bat` y `start_wisper_cli.bat`:

```powershell
git clone https://github.com/ilogicsoftwares/LiveVoice.git
cd LiveVoice
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r WisperLiveVoice\requirements.txt
```

Si ya descargaste el proyecto, omite `git clone` y entra a su carpeta. Si `py -3.12` no se reconoce, instala Python 3.12 x64 y abre otra terminal. El entorno virtual debe quedar en `LiveVoice\.venv`, **no** dentro de `WisperLiveVoice`.

Comprueba que la GPU puede realizar una inferencia. Este comando descargará una vez el modelo pequeño `tiny` para la prueba:

```powershell
.\.venv\Scripts\python.exe -c "import numpy as np; from faster_whisper import WhisperModel; m=WhisperModel('tiny',device='cuda',compute_type='float16'); list(m.transcribe(np.zeros(16000,dtype=np.float32),language='es',task='translate')[0]); print('CUDA OK')"
```

## 3. Variable de entorno y voz de ElevenLabs

En [ElevenLabs](https://elevenlabs.io/docs/eleven-api/quickstart), crea una API key que permita Text to Speech. **La única variable de entorno obligatoria para WisperLiveVoice** es:

| Variable | Valor | Obligatoria |
| --- | --- | --- |
| `ELEVENLABS_API_KEY` | Token secreto de ElevenLabs | Sí |

Guárdala como variable de usuario de Windows, sustituyendo el marcador por tu token:

```powershell
setx ELEVENLABS_API_KEY "TU_TOKEN_DE_ELEVENLABS"
```

Abre una **terminal nueva** después de `setx`. Verifica que existe sin imprimir el token:

```powershell
[bool]$env:ELEVENLABS_API_KEY
```

El programa también puede leer la variable de usuario directamente si la terminal estaba abierta antes de `setx`. `GEMINI_API_KEY` es exclusiva de la otra implementación y **no se usa aquí**. No guardes el token en el código, en los `.bat` ni en Git.

La **voz es un parámetro**, `--voice-id`, o un campo de la ventana. En ElevenLabs abre **My Voices → tres puntos de la voz → Copy voice ID** ([ayuda oficial](https://elevenlabs.io/docs/help-center/technical/how-do-i-find-the-voice-id-of-my-voices-via-the-website-and-api)). Usa el ID de una voz disponible en tu cuenta; algunas voces de la Voice Library tienen [restricciones de acceso por plan](https://elevenlabs.io/docs/eleven-creative/voices/voice-library).

## 4. Elegir el micrófono y el cable virtual

Desde la raíz del repositorio, lista los dispositivos:

```powershell
.\.venv\Scripts\python.exe WisperLiveVoice\live_voice.py --list-devices
```

Anota el número de tu **micrófono físico** para `--input` y el de **CABLE Input** (dispositivo de reproducción) para `--output`. Los índices cambian según el equipo o las conexiones. No elijas CABLE Output como entrada de WisperLiveVoice, porque podrías crear un bucle de audio.

En Teams entra a **Configuración → Dispositivos → Micrófono** y elige **CABLE Output** (dispositivo de grabación). Mantén los audífonos como altavoz de Teams para evitar que la llamada vuelva a entrar por tu micrófono.

## 5. Iniciar y comprobar

Desde la raíz puedes abrir por doble clic `start_wisper_gui.bat` para la ventana o `start_wisper_cli.bat` para la consola. En PowerShell:

```powershell
.\start_wisper_gui.bat
```

En la ventana revisa el micrófono, la salida, el ID de voz, **Sensibilidad**, **Pausa para enviar** y **Modelo ElevenLabs**; luego pulsa **Iniciar**. Verás el nivel del micrófono, la traducción (`EN:`), lo que dices (`ES:`) y el estado de ElevenLabs. La traducción se envía a ElevenLabs antes de calcular el texto en español de esa misma frase. Pulsa **Detener** para finalizar.

Al iniciar la versión de consola, indica los índices de tus dispositivos y el ID de tu voz:

```powershell
.\start_wisper_cli.bat --input 1 --output 8 --voice-id TU_VOICE_ID
```

### Elegir el modelo de voz

La opción predeterminada es **Flash v2.5** (`--tts-model flash`). Usa velocidad `0.73`, estabilidad `0.30`, similitud `1.0` y exageración de estilo `0`. La solicitud fija `language_code=es` aunque Whisper envíe texto traducido al inglés; esto puede influir en la pronunciación inglesa. Para probar una voz más expresiva usa **Eleven v3 Conversational** (`--tts-model v3`), que conserva sus ajustes independientes:

```powershell
.\start_wisper_cli.bat --input 1 --output 8 --voice-id TU_VOICE_ID --tts-model v3
```

En la ventana puedes cambiar **Modelo ElevenLabs** antes de pulsar Iniciar. También puedes abrirla con v3 seleccionado:

```powershell
.\start_wisper_gui.bat --tts-model v3
```

Ambos modelos usan el mismo Whisper `large-v3` para traducir. Solo cambia la generación de voz: Flash usa el WebSocket de Text to Speech; v3 Conversational usa el de Text to Dialogue. V3 puede sonar más expresivo, pero la latencia real depende de la frase, la red y el servicio. Elige Flash si necesitas la menor demora. [Comparación oficial de ElevenLabs](https://elevenlabs.io/docs/eleven-api/guides/how-to/websockets/tts-vs-ttd-websockets).

También puedes cambiar solo la voz inicial de la ventana:

```powershell
.\start_wisper_gui.bat --voice-id TU_VOICE_ID
```

O ejecutar el script directamente:

```powershell
.\.venv\Scripts\python.exe WisperLiveVoice\live_voice.py --input 1 --output 8 --voice-id TU_VOICE_ID
```

En consola usa `Ctrl+C` para terminar. Haz una llamada de prueba en Teams. La secuencia esperada es: sube el nivel del micrófono al hablar, aparece **voz detectada**, luego `EN:` y `ES:`, y después **ElevenLabs: llegó audio**. Los demás escucharán esa voz por CABLE Output; la aplicación no la reproduce en tus audífonos.

## Ajustes y solución de problemas

| Síntoma | Qué revisar |
| --- | --- |
| No aparece nivel de micrófono | Comprueba el índice de entrada, el permiso de micrófono en Windows y que otra aplicación no lo tenga bloqueado. |
| Hay nivel, pero no detecta frases | Baja **Sensibilidad (umbral)** en la ventana. En consola prueba `--mic-threshold 0.002`; un número menor es más sensible y puede captar ruido. El valor inicial es `0.004`. |
| Detecta voz, pero tarda en aparecer texto | Reduce **Pausa para enviar** de 600 a 400 ms en la ventana, o usa `--pause-ms 400` en consola. Una pausa demasiado corta puede partir frases y reducir la precisión de la traducción. Whisper traduce con `large-v3`; la primera carga descarga el modelo. En consola puedes usar `--whisper-model medium` o `small` para reducir trabajo, con posible pérdida de precisión. |
| Error de GPU o DLL CUDA/cuDNN | Ejecuta `nvidia-smi`, revisa CUDA 12, cuBLAS y cuDNN 9 en `PATH`, abre otra terminal y repite la prueba `CUDA OK`. |
| Falta `ELEVENLABS_API_KEY` | Ejecuta `setx` y abre otra terminal, o comprueba la variable de usuario de Windows. |
| Aparece `EN:`, pero no llega audio | Revisa el error en la consola o ventana, la API key, el permiso de Text to Speech, los créditos y que la voz esté disponible para tu cuenta. |
| ElevenLabs entrega audio, pero Teams no lo recibe | Verifica salida de la app = CABLE Input y micrófono de Teams = CABLE Output. Haz una llamada de prueba. |
| Error de frecuencia o dispositivo | Vuelve a listar los dispositivos. La app requiere entrada PCM mono a 16 kHz y salida PCM mono a 24 kHz. |

Whisper traduce voz **al inglés**. El idioma de entrada predeterminado es español; en consola se puede cambiar con `--source-language fr`, por ejemplo. El audio del micrófono se procesa localmente y **solo el texto traducido** se envía a ElevenLabs. No se vuelve a transcribir con Whisper el audio recibido de ElevenLabs para evitar otra inferencia en GPU y posible latencia.

Referencias: [Whisper](https://github.com/openai/whisper), [faster-whisper](https://github.com/SYSTRAN/faster-whisper), [ElevenLabs WebSocket TTS](https://elevenlabs.io/docs/eleven-api/guides/how-to/websockets/realtime-tts) y [VB-CABLE](https://vb-audio.com/Cable/).
