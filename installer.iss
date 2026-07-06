[Setup]
AppName=テーブル注文アプリ
AppVersion=1.0.0
AppPublisher=テーブル注文アプリ
DefaultDirName={localappdata}\Programs\LocalTableOrderApp
DefaultGroupName=テーブル注文アプリ
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
Name: "{autoprograms}\テーブル注文アプリ"; Filename: "{app}\LocalTableOrderApp.exe"
Name: "{autodesktop}\テーブル注文アプリ"; Filename: "{app}\LocalTableOrderApp.exe"; Tasks: desktopicon
Name: "{autoprograms}\テーブル注文アプリ フォルダを開く"; Filename: "{app}"

[Tasks]
Name: "desktopicon"; Description: "デスクトップにショートカットを作成する"; GroupDescription: "追加オプション:"; Flags: unchecked

[Run]
Filename: "{app}\LocalTableOrderApp.exe"; Description: "テーブル注文アプリ を起動する"; Flags: nowait postinstall skipifsilent
