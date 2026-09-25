# LiveVoice

LiveVoice offers **two independent versions** for translating your speech during a call. Both capture audio from a physical microphone and can send the translated voice to **CABLE Input** from [VB-CABLE](https://vb-audio.com/Cable/). In Teams, select **CABLE Output** as the microphone and use headphones to prevent call audio from feeding back into your physical microphone.

Download the Windows installers from the [latest release](https://github.com/ilogicsoftwares/LiveVoice/releases/latest). Each installer includes the application and its Python dependencies; you do not need to install Python or run `pip` to use it. If you want to run from source, follow the source installation steps below.

## 1. Google Gemini Live Translate

This version uses **Gemini Live Translate** for both translation and speech generation. The default target language is English; you can also choose other languages supported by Gemini. It requires an internet connection and the `GEMINI_API_KEY` environment variable. **An NVIDIA GPU is not required.**

Files: `translator.py` (command line), `translator_gui.py` (desktop window), `start_cli.bat`, and `start_gui.bat`.

### Install the Windows app

1. Download `GeminiLiveVoice-Setup-*-win64.exe` from the [latest release](https://github.com/ilogicsoftwares/LiveVoice/releases/latest) and run it. Launch **LiveVoice Gemini** from the Start menu.
2. Set your Google API key as a Windows user environment variable:

   ```powershell
   setx GEMINI_API_KEY "YOUR_GEMINI_API_KEY"
   ```

3. In the app, select your physical microphone, output device, and target language. For Teams, [install VB-CABLE](#3-install-the-vb-cable-virtual-microphone-on-windows) and select **CABLE Input** as the output.

The app reads the Windows user variable directly, so you can reopen it after `setx` without reinstalling. An internet connection and access to the Gemini Live Translate API are required.

### Run from source

Install Python 3.11 or later and VB-CABLE. In PowerShell, from the repository root:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
setx GEMINI_API_KEY "YOUR_GEMINI_API_KEY"
```

Open a new terminal after running `setx`. List audio devices to find the IDs of your physical microphone and **CABLE Input**:

```powershell
.\.venv\Scripts\python.exe translator.py --list-devices
```

### Run

Open the desktop window:

```powershell
.\start_gui.bat
```

Or run the command line version, replacing the example device IDs with yours:

```powershell
.\start_cli.bat --input 1 --output 5
```

Audio device IDs depend on your system; use the IDs returned by `--list-devices`. The desktop window lets you select the devices and target language. To translate into French from the command line, for example:

```powershell
.\start_cli.bat --input 1 --output 5 --target-language fr
```

List available target languages with `.\.venv\Scripts\python.exe translator.py --list-languages`. The desktop window shows input and output transcripts. The translated voice plays through the selected output device; if you choose CABLE Input, use a Teams test call to hear what other participants receive. Access to the Gemini model is required, and API usage may incur charges.

## 2. WisperLiveVoice: Whisper + ElevenLabs

This version uses **Whisper `large-v3` on an NVIDIA GPU** to translate Spanish speech into English and **ElevenLabs** to generate the voice. It requires an internet connection, the CUDA libraries described in the setup guide, and the `ELEVENLABS_API_KEY` environment variable. The voice ID is supplied as a command line option or entered in the desktop window. **This version does not use `GEMINI_API_KEY`.**

Files: `WisperLiveVoice/live_voice.py` (command line), `WisperLiveVoice/live_voice_gui.py` (desktop window), `start_wisper_cli.bat`, and `start_wisper_gui.bat`.

### Install the Windows app

1. Download `WisperLiveVoice-Setup-*-win64.exe` from the [latest release](https://github.com/ilogicsoftwares/LiveVoice/releases/latest) and run it. Launch **WisperLiveVoice** from the Start menu.
2. Set your ElevenLabs API key and a voice ID from your own ElevenLabs account as Windows user environment variables:

   ```powershell
   setx ELEVENLABS_API_KEY "YOUR_ELEVENLABS_API_KEY"
   setx ELEVENLABS_VOICE_ID "YOUR_VOICE_ID"
   ```

   The voice ID can also be entered or changed in the app.
3. In the app, select your physical microphone and output device. For Teams, [install VB-CABLE](#3-install-the-vb-cable-virtual-microphone-on-windows) and select **CABLE Input** as the output.

The installer includes the Python dependencies and CUDA runtime libraries, so a separate Python or CUDA Toolkit installation is not needed. A compatible **NVIDIA GPU and driver** are still required. On the first run, Whisper downloads the `large-v3` model (about 3 GB) automatically; allow time, internet access, and disk space for that download. The app uses the cached model on later runs.

### Run from source

Follow the [detailed WisperLiveVoice setup guide (Spanish)](WisperLiveVoice/INSTALACION.md) to install Python 3.12, CUDA/cuDNN, and VB-CABLE, and to verify that Whisper runs on the GPU. From the repository root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r WisperLiveVoice\requirements.txt
setx ELEVENLABS_API_KEY "YOUR_ELEVENLABS_API_KEY"
```

If you already created `.venv` for Gemini with a compatible Python version, you can skip the first command and install the additional dependencies in the same environment. Open a new terminal after running `setx`. Choose a voice from your ElevenLabs account in the desktop window or pass its ID with `--voice-id` on the command line.

### Run

Open the desktop window to select the microphone, output device, voice, and ElevenLabs model:

```powershell
.\start_wisper_gui.bat
```

For the command line version, list audio devices first, then replace the example IDs and voice ID with yours:

```powershell
.\.venv\Scripts\python.exe WisperLiveVoice\live_voice.py --list-devices
.\start_wisper_cli.bat --input 1 --output 5 --voice-id YOUR_VOICE_ID
```

The default voice model is **ElevenLabs Flash v2.5**. Select **v3 Conversational** in the desktop window or add `--tts-model v3` to the command line. Whisper waits for a 600 ms pause by default before sending each phrase. You can change this with the **Pausa para enviar** (pause before sending) field in the desktop window or with `--pause-ms` on the command line. A shorter pause may reduce translation accuracy. The [detailed setup guide (Spanish)](WisperLiveVoice/INSTALACION.md) covers microphone sensitivity, troubleshooting, and Teams setup.

## 3. Install the VB-CABLE virtual microphone on Windows

These steps apply to **both versions**. VB-CABLE creates two devices: **CABLE Input** receives the audio played by LiveVoice, and **CABLE Output** makes that audio available to Teams as a microphone. [VB-Audio describes this connection on its official site](https://vb-audio.com/Cable/).

1. Download **VB-CABLE Virtual Audio Device** for Windows from the [official VB-Audio page](https://vb-audio.com/Cable/).
2. Extract **all** files from the ZIP archive into a local folder. Do not run the installer from inside the ZIP archive.
3. On 64-bit Windows, right-click `VBCABLE_Setup_x64.exe` and select **Run as administrator**. On 32-bit Windows, use `VBCABLE_Setup.exe`. Complete the installation and restart your computer. See the [official installation manual](https://vb-audio.com/Cable/VBCABLE_ReferenceManual.pdf).
4. Open **Windows Settings → System → Sound** and check that **CABLE Input** appears among output/playback devices and **CABLE Output** among input/recording devices. If Windows changed your default devices, select your headphones and physical microphone again.
5. In either LiveVoice version, select your **physical microphone** as the input and **CABLE Input** as the output. In **Teams → Settings → Devices**, select **CABLE Output** as the microphone and your headphones as the speaker.
6. Make a Teams test call. If no audio reaches Teams, check that LiveVoice sends audio to CABLE Input and Teams listens to CABLE Output. Do not select CABLE Output as the LiveVoice input, as that would create a feedback loop.
