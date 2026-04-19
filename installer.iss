; installer.iss - Скрипт сборки инсталлятора для SecureCopyGuard

[Setup]
; Уникальный идентификатор приложения (не меняй его)
AppId={{8A4B6C2D-1234-4567-89AB-CDEF01234567}
AppName=SecureCopyGuard Endpoint DLP
AppVersion=3.0 Enterprise
AppPublisher=Rahat Aliev Security
AppPublisherURL=https://github.com/Meriodasuzwe
AppSupportURL=https://github.com/Meriodasuzwe
AppUpdatesURL=https://github.com/Meriodasuzwe

; Куда будет устанавливаться программа по умолчанию
DefaultDirName={autopf}\SecureCopyGuard
DefaultGroupName=SecureCopyGuard

; Имя выходного файла установщика
OutputDir=Output
OutputBaseFilename=SecureCopyGuard_Setup_v3
SetupIconFile=compiler:SetupClassicIcon.ico
Compression=lzma2/ultra64
SolidCompression=yes

; Запрашиваем права администратора для установки (обязательно для DLP!)
PrivilegesRequired=admin

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Берем ВСЕ файлы из папки dist и кладем в папку установки
Source: "dist\SecureCopyGuard\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Dirs]
; Даем обычным пользователям права на запись в папку программы, 
; чтобы программа могла обновлять config.json и базу данных без вылетов
Name: "{app}"; Permissions: users-modify

[Icons]
Name: "{group}\SecureCopyGuard"; Filename: "{app}\SecureCopyGuard.exe"
Name: "{group}\{cm:UninstallProgram,SecureCopyGuard}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\SecureCopyGuard"; Filename: "{app}\SecureCopyGuard.exe"; Tasks: desktopicon

[Run]
; Запуск программы сразу после установки
Filename: "{app}\SecureCopyGuard.exe"; Description: "{cm:LaunchProgram,SecureCopyGuard}"; Flags: nowait postinstall skipifsilent