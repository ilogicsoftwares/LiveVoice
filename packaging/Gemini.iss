#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif

[Setup]
AppId={{B9741827-BBD7-4F9A-A9A6-7A41BC8E0374}
AppName=LiveVoice Gemini
AppVersion={#AppVersion}
AppPublisher=LiveVoice
DefaultDirName={localappdata}\Programs\LiveVoice Gemini
DefaultGroupName=LiveVoice Gemini
OutputDir=..\build\release
OutputBaseFilename=GeminiLiveVoice-Setup-{#AppVersion}-win64
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
UninstallDisplayIcon={app}\GeminiLiveVoice.exe
WizardStyle=modern

[Files]
Source: "..\build\dist\GeminiLiveVoice\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\LiveVoice Gemini"; Filename: "{app}\GeminiLiveVoice.exe"
Name: "{autodesktop}\LiveVoice Gemini"; Filename: "{app}\GeminiLiveVoice.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Run]
Filename: "{app}\GeminiLiveVoice.exe"; Description: "Launch LiveVoice Gemini"; Flags: nowait postinstall skipifsilent
