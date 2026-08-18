; Inno Setup script for X-ray Explorer.
;
; Not run directly -- packaging/build.py supplies the paths:
;   ISCC /DAppVersion=1.0.0 /DSourceDir=... /DOutputDir=... /DProjectRoot=... installer.iss

#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
#ifndef SourceDir
  #define SourceDir "..\..\dist\X-ray Explorer"
#endif
#ifndef OutputDir
  #define OutputDir "..\..\dist\installer"
#endif
#ifndef ProjectRoot
  #define ProjectRoot "..\.."
#endif

#define AppName        "X-ray Explorer"
#define AppExeName     "XrayExplorer.exe"
#define AppPublisher   "Matthew Wormington"
#define AppContact     "m_wormington@hotmail.com"
#define AppURL         "https://github.com/tschoonj/xraylib"

[Setup]
AppId={{7C2B9E14-4E9A-4F3B-9E0A-5D2C1B8A63F1}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppContact={#AppContact}
VersionInfoCompany={#AppPublisher}
VersionInfoCopyright=Copyright (C) 2026 {#AppPublisher}
VersionInfoVersion={#AppVersion}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
LicenseFile={#ProjectRoot}\LICENSE
InfoAfterFile={#ProjectRoot}\THIRD-PARTY-NOTICES.md
OutputDir={#OutputDir}
OutputBaseFilename={#StringChange(AppName, " ", "")}-{#AppVersion}-windows-x64-setup
SetupIconFile={#ProjectRoot}\packaging\icon.ico
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName} {#AppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
; Per-user installs need no admin rights; the user picks on the first page.
PrivilegesRequiredOverridesAllowed=dialog
; "x64" rather than the newer "x64compatible" so this compiles on Inno Setup
; 6.0-6.2 as well as 6.3+.
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; \
    GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; The whole PyInstaller onedir tree. Qt stays as separate DLLs, which is what
; the LGPL requires so users can substitute their own Qt build.
Source: "{#SourceDir}\*"; DestDir: "{app}"; \
    Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; \
    Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; \
    Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Remove __pycache__ and any stray files created next to the install.
Type: filesandordirs; Name: "{app}"
