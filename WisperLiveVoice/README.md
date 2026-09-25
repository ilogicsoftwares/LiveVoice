# WisperLiveVoice

Translate Spanish speech into English with Whisper `large-v3` on an NVIDIA GPU, then generate the translated voice with ElevenLabs. For Teams, the output can be routed through VB-CABLE.

For Windows installation without Python, download `WisperLiveVoice-Setup-*-win64.exe` from the [latest release](https://github.com/ilogicsoftwares/LiveVoice/releases/latest). The installer includes the app, Python dependencies, and CUDA runtime libraries. You still need a compatible NVIDIA GPU and driver. The `large-v3` model downloads automatically on first use (about 3 GB).

Set the API key and, optionally, your default voice ID as Windows user environment variables:

```powershell
setx ELEVENLABS_API_KEY "YOUR_ELEVENLABS_API_KEY"
setx ELEVENLABS_VOICE_ID "YOUR_VOICE_ID"
```

Launch **WisperLiveVoice** from the Start menu. Select your physical microphone and output device in the window; select **CABLE Input** as the output if you use VB-CABLE with Teams. You can edit the voice ID in the window. See the [main README](../README.md#3-install-the-vb-cable-virtual-microphone-on-windows) for VB-CABLE installation.

The [detailed installation and usage guide (Spanish)](INSTALACION.md) covers Windows and CUDA requirements, Python setup, the `ELEVENLABS_API_KEY` environment variable, voice and device selection, launchers, Teams testing, and troubleshooting.

After completing setup, start the desktop window from the repository root:

```powershell
.\start_wisper_gui.bat
```

For the command line version, replace the placeholders with your audio device IDs and ElevenLabs voice ID:

```powershell
.\start_wisper_cli.bat --input YOUR_MIC_ID --output YOUR_CABLE_INPUT_ID --voice-id YOUR_VOICE_ID
```

This version requires only one application-specific environment variable: `ELEVENLABS_API_KEY`. Pass the voice ID as an option or enter it in the desktop window. Whisper always runs on the GPU. Microphone audio is processed locally; only the translated text is sent to ElevenLabs.

ElevenLabs Flash v2.5 is the default voice model. To try Eleven v3 Conversational, select **Modelo ElevenLabs** (ElevenLabs model) in the desktop window or add `--tts-model v3` to the command line.

Flash v2.5 sends speed `0.73`, stability `0.30`, similarity `1.0`, style `0`, and language `es`. V3 keeps its own settings.
