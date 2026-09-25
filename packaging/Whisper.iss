#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif

[Setup]
AppId={{1CE91764-A223-48A0-BE39-B622D248B451}
AppName=WisperLiveVoice
AppVersion={#AppVersion}
AppPublisher=LiveVoice
DefaultDirName={localappdata}\Programs\WisperLiveVoice
DefaultGroupName=WisperLiveVoice
OutputDir=..\build\release
OutputBaseFilename=WisperLiveVoice-Setup-{#AppVersion}-win64
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
UninstallDisplayIcon={app}\WisperLiveVoice.exe
WizardStyle=modern

[Files]
Source: "..\build\dist\WisperLiveVoice\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\WisperLiveVoice\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\WisperLiveVoice\INSTALACION.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\WisperLiveVoice"; Filename: "{app}\WisperLiveVoice.exe"
Name: "{autodesktop}\WisperLiveVoice"; Filename: "{app}\WisperLiveVoice.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Run]
Filename: "{app}\WisperLiveVoice.exe"; Description: "Launch WisperLiveVoice"; Flags: nowait postinstall skipifsilent
