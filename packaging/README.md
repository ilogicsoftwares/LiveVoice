# Build the Windows installers

The release contains two independent graphical installers:

- `GeminiLiveVoice-Setup-VERSION-win64.exe`
- `WisperLiveVoice-Setup-VERSION-win64.exe`

Each installer includes the corresponding Python application and dependencies. The Whisper installer also includes the CUDA 12 runtime libraries needed by CTranslate2 and a separate console engine used by the GUI. The `large-v3` model is downloaded automatically on first use and then cached for the current Windows user. The model is not part of the installer because it is about 3 GB and GitHub limits each release asset to 2 GiB.

## Build machine

Use Windows x64 with Python 3.12, Inno Setup 6, and the CUDA 12 `bin` directory containing `cublas64_12.dll`, `cublasLt64_12.dll`, and `cudart64_12.dll`. Install the dependencies in a virtual environment at the repository root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r WisperLiveVoice\requirements.txt -r packaging\requirements-build.txt
winget install --id JRSoftware.InnoSetup -e --accept-package-agreements --accept-source-agreements
```

Build both installers:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File packaging\build.ps1 -Version 0.1.0
```

If the CUDA libraries are outside the normal Toolkit path, pass `-CudaBin "C:\path\to\CUDA\bin"`. The build creates the installers and `SHA256SUMS.txt` in `build\release`. `build\` is ignored by Git.

To verify the bundled Whisper engine before publishing:

```powershell
.\build\dist\WisperLiveVoice\engine\WisperLiveVoiceEngine.exe --self-test
```

This downloads the model if it is not already cached and runs a short GPU inference. Also install each generated setup executable and launch its GUI to confirm that devices are listed. A target computer still needs a compatible NVIDIA GPU and driver for Whisper, plus VB-CABLE if the voice should appear as a microphone in Teams.
