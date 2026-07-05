[Setup]
AppName=Local Table Order App
AppVersion=1.0.0
AppPublisher=Local Table Order App
DefaultDirName={localappdata}\Programs\LocalTableOrderApp
DefaultGroupName=Local Table Order App
OutputDir=installer
OutputBaseFilename=LocalTableOrderApp_Setup
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest
DisableProgramGroupPage=yes

[Languages]
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"

[Files]
Source: "dist\LocalTableOrderApp\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Local Table Order App"; Filename: "{app}\LocalTableOrderApp.exe"
Name: "{autodesktop}\Local Table Order App"; Filename: "{app}\LocalTableOrderApp.exe"; Tasks: desktopicon
Name: "{autoprograms}\Local Table Order App フォルダを開く"; Filename: "{app}"

[Tasks]
Name: "desktopicon"; Description: "デスクトップにショートカットを作成する"; GroupDescription: "追加オプション:"; Flags: unchecked

[Run]
Filename: "{app}\LocalTableOrderApp.exe"; Description: "Local Table Order App を起動する"; Flags: nowait postinstall skipifsilent
