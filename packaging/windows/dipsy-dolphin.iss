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

#ifndef ModelDownloadUrl
  #error ModelDownloadUrl must be defined.
#endif

#ifndef ModelFilename
  #error ModelFilename must be defined.
#endif

#ifndef ModelInstallSubdir
  #define ModelInstallSubdir "default"
#endif

#ifndef ModelSizeBytes
  #error ModelSizeBytes must be defined.
#endif

#ifndef ModelSha256
  #error ModelSha256 must be defined.
#endif

#ifndef RuntimeDownloadUrl
  #error RuntimeDownloadUrl must be defined.
#endif

#ifndef RuntimeArchiveName
  #error RuntimeArchiveName must be defined.
#endif

#ifndef RuntimeExtractedSize
  #error RuntimeExtractedSize must be defined.
#endif

#ifndef RuntimeArchiveSha256
  #error RuntimeArchiveSha256 must be defined.
#endif

#ifndef CudaDownloadUrl
  #error CudaDownloadUrl must be defined.
#endif

#ifndef CudaArchiveName
  #error CudaArchiveName must be defined.
#endif

#ifndef CudaExtractedSize
  #error CudaExtractedSize must be defined.
#endif

#ifndef CudaArchiveSha256
  #error CudaArchiveSha256 must be defined.
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
ArchiveExtraction=full
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#AppExeName}
InfoBeforeFile="online-installer-info.txt"

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#ModelDownloadUrl}"; DestDir: "{app}\models\{#ModelInstallSubdir}"; DestName: "{#ModelFilename}"; ExternalSize: {#ModelSizeBytes}; Hash: "{#ModelSha256}"; Flags: external download ignoreversion
Source: "{#RuntimeDownloadUrl}"; DestDir: "{app}\runtime"; DestName: "{#RuntimeArchiveName}"; ExternalSize: {#RuntimeExtractedSize}; Hash: "{#RuntimeArchiveSha256}"; Flags: external download extractarchive ignoreversion recursesubdirs createallsubdirs
Source: "{#CudaDownloadUrl}"; DestDir: "{app}\runtime"; DestName: "{#CudaArchiveName}"; ExternalSize: {#CudaExtractedSize}; Hash: "{#CudaArchiveSha256}"; Flags: external download extractarchive ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent
