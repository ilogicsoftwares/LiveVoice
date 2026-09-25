param(
    [ValidatePattern('^\d+\.\d+\.\d+$')]
    [string]$Version = '0.1.0',
    [string]$CudaBin
)

$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$build = [IO.Path]::GetFullPath((Join-Path $root 'build'))
if (-not $build.StartsWith($root + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Build directory is outside the repository: $build"
}
$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    throw 'Create .venv and install both application requirements plus packaging/requirements-build.txt first.'
}

$isccCandidates = @(
    (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe'),
    (Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe'),
    (Join-Path $env:ProgramFiles 'Inno Setup 6\ISCC.exe')
)
$iscc = $isccCandidates | Where-Object { $_ -and (Test-Path -LiteralPath $_) } | Select-Object -First 1
if (-not $iscc) {
    throw 'Inno Setup 6 is required. Install JRSoftware.InnoSetup with winget.'
}

if (-not $CudaBin) {
    if ($env:CUDA_PATH -and (Test-Path -LiteralPath (Join-Path $env:CUDA_PATH 'bin\cublas64_12.dll'))) {
        $CudaBin = Join-Path $env:CUDA_PATH 'bin'
    } else {
        $cudaRoot = Join-Path $env:ProgramFiles 'NVIDIA GPU Computing Toolkit\CUDA'
        $CudaBin = Get-ChildItem -LiteralPath $cudaRoot -Directory -ErrorAction SilentlyContinue |
            Sort-Object Name -Descending |
            ForEach-Object { Join-Path $_.FullName 'bin' } |
            Where-Object { Test-Path -LiteralPath (Join-Path $_ 'cublas64_12.dll') } |
            Select-Object -First 1
    }
}
if (-not $CudaBin) { throw 'CUDA 12 runtime libraries were not found. Pass -CudaBin with the CUDA bin directory.' }
$cudaDlls = @('cublas64_12.dll', 'cublasLt64_12.dll', 'cudart64_12.dll')
foreach ($dll in $cudaDlls) {
    if (-not (Test-Path -LiteralPath (Join-Path $CudaBin $dll))) {
        throw "Missing CUDA runtime library: $dll in $CudaBin"
    }
}

if (Test-Path -LiteralPath $build) {
    Remove-Item -LiteralPath $build -Recurse -Force
}
New-Item -ItemType Directory -Path (Join-Path $build 'dist'), (Join-Path $build 'release'), (Join-Path $build 'spec') -Force | Out-Null
$common = @('--noconfirm', '--clean', '--log-level=WARN', '--distpath', (Join-Path $build 'dist'), '--specpath', (Join-Path $build 'spec'))

function Invoke-PyInstaller([string]$name, [string]$entry, [string[]]$options) {
    Write-Host "Building $name..."
    & $python -m PyInstaller @common '--workpath' (Join-Path $build "work\$name") '--name' $name '--onedir' @options $entry
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed for $name" }
}

Invoke-PyInstaller 'GeminiLiveVoice' (Join-Path $root 'translator_gui.py') @(
    '--windowed', '--collect-all', 'google.genai', '--collect-all', 'sounddevice'
)
Invoke-PyInstaller 'WisperLiveVoice' (Join-Path $root 'WisperLiveVoice\live_voice_gui.py') @(
    '--windowed', '--collect-all', 'sounddevice'
)
$engineOptions = @(
    '--console', '--runtime-hook', (Join-Path $PSScriptRoot 'rthook_cuda.py'),
    '--collect-all', 'faster_whisper', '--collect-all', 'ctranslate2',
    '--collect-all', 'huggingface_hub', '--collect-all', 'onnxruntime',
    '--collect-all', 'tokenizers', '--collect-all', 'av',
    '--collect-all', 'sounddevice', '--collect-all', 'websockets'
)
foreach ($dll in $cudaDlls) {
    $engineOptions += @('--add-binary', "$(Join-Path $CudaBin $dll);.")
}
Invoke-PyInstaller 'WisperLiveVoiceEngine' (Join-Path $root 'WisperLiveVoice\live_voice.py') $engineOptions

$whisperGui = Join-Path $build 'dist\WisperLiveVoice'
$whisperEngine = Join-Path $build 'dist\WisperLiveVoiceEngine'
Copy-Item -LiteralPath $whisperEngine -Destination (Join-Path $whisperGui 'engine') -Recurse -Force

Write-Host 'Compiling installers...'
& $iscc '/Qp' "/DAppVersion=$Version" (Join-Path $PSScriptRoot 'Gemini.iss')
if ($LASTEXITCODE -ne 0) { throw 'Inno Setup failed for Gemini' }
& $iscc '/Qp' "/DAppVersion=$Version" (Join-Path $PSScriptRoot 'Whisper.iss')
if ($LASTEXITCODE -ne 0) { throw 'Inno Setup failed for Whisper' }

$installers = Get-ChildItem -LiteralPath (Join-Path $build 'release') -Filter '*-Setup-*.exe' -File
if ($installers.Count -ne 2) { throw "Expected two installers, found $($installers.Count)" }
$hashes = $installers | Sort-Object Name | ForEach-Object {
    $hash = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    "$hash  $($_.Name)"
}
[IO.File]::WriteAllLines((Join-Path $build 'release\SHA256SUMS.txt'), [string[]]$hashes)
Write-Host "Installers ready in $(Join-Path $build 'release')"
