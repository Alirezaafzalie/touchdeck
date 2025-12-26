  #define AppName "TouchDeck"
  #define AppVersion "1.0.0"
  #define AppPublisher "Your Name"
  #define AppExeName "TouchDeck.exe"

  ; ===== Choose ONE of these =====
  ; If you built ONE-FILE EXE:
  #define AppSourceDir "C:\Users\TempAdmin\Documents\python\dist"
  ; If you built FOLDER EXE:
  ;#define AppSourceDir "C:\Users\TempAdmin\Documents\python\dist\TouchDeck"

  [Setup]
  AppId={{9A2D3B07-0E35-4F64-9C5B-4C3A3D3D5E0F}
  AppName={#AppName}
  AppVersion={#AppVersion}
  AppPublisher={#AppPublisher}
  DefaultDirName={autopf}\{#AppName}
  DefaultGroupName={#AppName}
  OutputDir=C:\Users\TempAdmin\Documents\python\dist\installer
  OutputBaseFilename=TouchDeckSetup
  SetupIconFile=C:\Users\TempAdmin\Documents\python\touchdeck\SDE.ico
  UninstallDisplayIcon={app}\{#AppExeName}
  Compression=lzma
  SolidCompression=yes
  PrivilegesRequired=admin

  [Files]
  Source: "{#AppSourceDir}\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion
  ; If you built FOLDER EXE, include all files:
  ;Source: "{#AppSourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

  ; Optional: include a default config next to the EXE
  Source: "C:\Users\TempAdmin\Documents\python\touchdeck\touchdeck.json"; DestDir: "{app}"; Flags: ignoreversion onlyifdestfileexists

  [Icons]
  Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
  Name: "{commondesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

  [Tasks]
  Name: "desktopicon"; Description: "Create a desktop icon"; GroupDescription: "Additional icons:"; Flags:unchecked

  [Run]
  Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent