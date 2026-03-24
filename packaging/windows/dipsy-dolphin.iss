#ifndef SourceDir
  #error SourceDir must be defined.
#endif

#ifndef OutputDir
  #error OutputDir must be defined.
#endif

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

#ifndef OutputBaseName
  #define OutputBaseName "DipsyDolphin-Setup"
#endif

#ifndef ModelDisplayName
  #define ModelDisplayName "Bundled local model"
#endif

#ifndef ModelSourceDir
  #error ModelSourceDir must be defined.
#endif

#ifndef RuntimeSourceDir
  #error RuntimeSourceDir must be defined.
#endif

#define AppName "Dipsy Dolphin"
#define AppExeName "DipsyDolphin.exe"
#define AppPublisher "Dipsy Dolphin Project"
#define AppId "DipsyDolphinDesktopAssistant"

[Setup]
AppId={#AppId}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppComments=Bundled local companion model: {#ModelDisplayName}
DefaultDirName={localappdata}\Programs\Dipsy Dolphin
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir={#OutputDir}
OutputBaseFilename={#OutputBaseName}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#AppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#ModelSourceDir}\*"; DestDir: "{app}\models"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#RuntimeSourceDir}\*"; DestDir: "{app}\runtime"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent
