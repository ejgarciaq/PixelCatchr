; Script de Inno Setup para PixelCatchr
; Requiere Inno Setup Compiler para generar el instalador final .exe

#define MyAppName "PixelCatchr"
#define MyAppVersion "1.0"
#define MyAppPublisher "Webtechcrafter"
#define MyAppURL "https://www.webtechcrafter.com/"
#define MyAppExeName "run.exe"

[Setup]
; Identificador único de la aplicación
AppId={{C12B5819-1234-4567-89AB-CDEF01234567}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
; Quita el punto y coma de la siguiente linea si tienes un archivo .ico en assets
; SetupIconFile=assets\icon.ico
OutputDir=Output
OutputBaseFilename=PixelCatchr_Setup_v1.0
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Asegúrate de que has ejecutado 'pyinstaller run.spec' antes de compilar este script
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
; Agrega aquí otros archivos si es necesario (ej. carpetas de recursos adicionales si no usarás --onefile)

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent
