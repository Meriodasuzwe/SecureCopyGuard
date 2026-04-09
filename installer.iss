[Setup]
AppName=SecureCopyGuard DLP
AppVersion=2.1 Enterprise
AppPublisher=Zhandos Security
; Изменили путь установки на AppData/Local (не требует прав админа для записи логов)
DefaultDirName={localappdata}\SecureCopyGuard
DefaultGroupName=SecureCopyGuard
UninstallDisplayIcon={app}\SecureCopyGuard.exe
Compression=lzma2
SolidCompression=yes
OutputDir=.\Output
OutputBaseFilename=Install_SecureCopyGuard

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на Рабочем столе"; GroupDescription: "Дополнительные значки:"; Flags: unchecked

[Files]
; Забираем всю папку dist вместе с нашим вшитым config.json
Source: "dist\SecureCopyGuard\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\SecureCopyGuard"; Filename: "{app}\SecureCopyGuard.exe"
Name: "{group}\Удалить SecureCopyGuard"; Filename: "{uninstallexe}"
Name: "{autodesktop}\SecureCopyGuard"; Filename: "{app}\SecureCopyGuard.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\SecureCopyGuard.exe"; Description: "Запустить Endpoint Agent"; Flags: nowait postinstall skipifsilent