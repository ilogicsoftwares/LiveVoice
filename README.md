# LiveVoice

LiveVoice ofrece **dos versiones independientes** para traducir tu voz durante una llamada. Ambas toman audio del micrófono físico y pueden enviar la voz traducida a **CABLE Input** de [VB-CABLE](https://vb-audio.com/Cable/). En Teams selecciona **CABLE Output** como micrófono y usa audífonos para evitar que el audio de la llamada vuelva a entrar por el micrófono físico.

## 1. Google Gemini Live Translate

Esta versión usa **Gemini Live Translate** para traducir y generar la voz. El idioma destino predeterminado es inglés; también puedes elegir otros idiomas admitidos por Gemini. Necesita Internet y la variable de entorno `GEMINI_API_KEY`. **No requiere GPU NVIDIA.**

Archivos: `translator.py` (consola), `translator_gui.py` (ventana), `start_cli.bat` y `start_gui.bat`.

### Instalación

Instala Python 3.11 o posterior y VB-CABLE. Desde PowerShell, en la raíz del repositorio:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
setx GEMINI_API_KEY "TU_API_KEY_DE_GEMINI"
```

Abre una terminal nueva después de `setx`. Para encontrar los números de tu micrófono físico y de **CABLE Input**:

```powershell
.\.venv\Scripts\python.exe translator.py --list-devices
```

### Ejecución

Para abrir la ventana:

```powershell
.\start_gui.bat
```

Para usar la consola, reemplaza los índices por los de tu equipo:

```powershell
.\start_cli.bat --input 1 --output 5
```

Los índices de audio dependen de los dispositivos conectados; usa los que obtuviste con `--list-devices`. En la GUI puedes elegir los dispositivos y el idioma destino. Para cambiar el idioma en consola, por ejemplo a francés:

```powershell
.\start_cli.bat --input 1 --output 5 --target-language fr
```

Consulta los idiomas disponibles con `.\.venv\Scripts\python.exe translator.py --list-languages`. La ventana muestra las transcripciones de entrada y salida. La voz traducida sale por el dispositivo que elegiste; si es CABLE Input, escúchala con una llamada de prueba de Teams. Gemini requiere acceso al modelo y su API puede generar costes.

## 2. WisperLiveVoice: Whisper + ElevenLabs

Esta versión usa **Whisper `large-v3` en una GPU NVIDIA** para traducir la voz del español al inglés y **ElevenLabs** para generar la voz. Necesita Internet, CUDA con las bibliotecas indicadas en la guía y la variable de entorno `ELEVENLABS_API_KEY`. El ID de voz es un parámetro o un campo de la ventana. **No usa `GEMINI_API_KEY`.**

Archivos: `WisperLiveVoice/live_voice.py` (consola), `WisperLiveVoice/live_voice_gui.py` (ventana), `start_wisper_cli.bat` y `start_wisper_gui.bat`.

### Instalación

Sigue la **[guía completa de WisperLiveVoice](WisperLiveVoice/INSTALACION.md)** para instalar Python 3.12, CUDA/cuDNN y VB-CABLE, además de comprobar que Whisper funciona en GPU. Desde la raíz del repositorio:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r WisperLiveVoice\requirements.txt
setx ELEVENLABS_API_KEY "TU_TOKEN_DE_ELEVENLABS"
```

Si ya creaste `.venv` para Gemini con una versión de Python compatible, puedes omitir la primera línea e instalar las dependencias adicionales en el mismo entorno. Abre una terminal nueva después de `setx`. Elige una voz de tu cuenta de ElevenLabs en la ventana o pásala con `--voice-id` en consola.

### Ejecución

Para abrir la ventana y seleccionar micrófono, salida, voz y modelo de ElevenLabs:

```powershell
.\start_wisper_gui.bat
```

Para la consola, averigua primero los índices de dispositivos y después sustitúyelos junto con el ID de voz:

```powershell
.\.venv\Scripts\python.exe WisperLiveVoice\live_voice.py --list-devices
.\start_wisper_cli.bat --input 1 --output 5 --voice-id TU_VOICE_ID
```

El modelo de voz predeterminado es **ElevenLabs Flash v2.5**. Puedes elegir **v3 Conversational** en la ventana o añadir `--tts-model v3` al comando de consola. Whisper espera una pausa de 600 ms por defecto antes de enviar cada frase; la GUI permite ajustar **Pausa para enviar** y la consola acepta `--pause-ms`. Una pausa demasiado corta puede reducir la precisión de la traducción. La [guía de instalación](WisperLiveVoice/INSTALACION.md) incluye ajustes de sensibilidad, solución de problemas y la configuración de Teams.

## 3. Instalar el micrófono virtual VB-CABLE en Windows

Este paso sirve para **ambas versiones**. VB-CABLE crea dos dispositivos: **CABLE Input** recibe el audio que reproduce LiveVoice y **CABLE Output** lo presenta como micrófono a Teams. [VB-Audio explica esa conexión en su sitio oficial](https://vb-audio.com/Cable/).

1. Descarga el paquete **VB-CABLE Virtual Audio Device** desde la [página oficial de VB-Audio](https://vb-audio.com/Cable/). Elige el paquete de Windows.
2. Extrae **todos** los archivos del ZIP a una carpeta local. No ejecutes el instalador desde dentro del ZIP.
3. En Windows de 64 bits, haz clic derecho en `VBCABLE_Setup_x64.exe` y selecciona **Ejecutar como administrador**. En Windows de 32 bits usa `VBCABLE_Setup.exe`. Sigue el instalador y reinicia el equipo. [Manual oficial de instalación](https://vb-audio.com/Cable/VBCABLE_ReferenceManual.pdf).
4. Abre **Configuración de Windows → Sistema → Sonido** y comprueba que aparezcan **CABLE Input** entre los dispositivos de salida/reproducción y **CABLE Output** entre los de entrada/grabación. Si Windows cambió los dispositivos predeterminados, vuelve a seleccionar tus audífonos y tu micrófono físico.
5. En la versión de LiveVoice que uses, selecciona tu **micrófono físico** como entrada y **CABLE Input** como salida. En **Teams → Configuración → Dispositivos**, selecciona **CABLE Output** como micrófono y tus audífonos como altavoz.
6. Haz una llamada de prueba en Teams. Si no llega audio, confirma que la aplicación envía la voz a CABLE Input y que Teams escucha CABLE Output. No elijas CABLE Output como entrada de LiveVoice, porque se crearía un bucle.
