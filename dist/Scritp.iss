; Script generado por el Asistente de Scripts de Inno Setup.
; ¡CONSULTE LA DOCUMENTACIÓN PARA MÁS DETALLES SOBRE LA CREACIÓN DE ARCHIVOS SCRIPT DE INNO SETUP!
; Solo para uso no comercial

; --- DEFINICIÓN DE VARIABLES GLOBALES ---
#define MyAppName "PixelCatchr"
#define MyAppVersion "1.0"
#define MyAppPublisher "Webtechcrafter"
#define MyAppURL "https://www.webtechcrafter.com/"
#define MyAppExeName "PixelCatchr.exe"
#define MyAppAssocName MyAppName + " File"
#define MyAppAssocExt ".myp"
#define MyAppAssocKey StringChange(MyAppAssocName, " ", "") + MyAppAssocExt

[Setup]
; NOTA: El valor de AppId identifica de forma única a esta aplicación. No uses el mismo AppId en instaladores de otras apps.
AppId={{FF5F0907-D36D-4EB2-A373-CC9E632B069D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
; Directorio por defecto en Archivos de Programa (Program Files)
DefaultDirName={autopf}\{#MyAppName}
; Icono que se mostrará en el Panel de Control para la desinstalación
UninstallDisplayIcon={app}\{#MyAppExeName}
; Restringe la instalación solo a sistemas compatibles con x64 y Windows 11 en Arm
ArchitecturesAllowed=x64compatible
; Fuerza a que en sistemas de 64 bits se instale en la carpeta nativa de 64 bits y use registros de 64 bits
ArchitecturesInstallIn64BitMode=x64compatible
ChangesAssociations=yes
DisableProgramGroupPage=yes
; Rutas de los archivos de texto informativos y de licencia
LicenseFile=D:\Workspace\PixelCatchr\dist\Documentos\LICENSE.txt
InfoBeforeFile=D:\Workspace\PixelCatchr\dist\Documentos\README_AFTER_INSTALL.txt
InfoAfterFile=D:\Workspace\PixelCatchr\dist\Documentos\README_BEFORE_INSTALL.txt
PrivilegesRequiredOverridesAllowed=dialog
; Nombre del archivo ejecutable del instalador resultante
OutputBaseFilename=PixelCatchr_Setup
SetupIconFile=D:\Workspace\PixelCatchr\assets\icon.ico
SolidCompression=yes
WizardStyle=modern dynamic

[Languages]
; Idiomas disponibles en el asistente (priorizando el español)
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
; Tarea opcional para crear un acceso directo en el escritorio
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Archivo ejecutable principal de la aplicación
Source: "D:\Workspace\PixelCatchr\dist\PixelCatchr\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
; Carpeta interna generada por PyInstaller con todas las dependencias y librerías
Source: "D:\Workspace\PixelCatchr\dist\PixelCatchr\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs

[Registry]
; Configuración del registro de Windows para asociar la extensión de archivo configurada (.myp)
Root: HKA; Subkey: "Software\Classes\{#MyAppAssocExt}\OpenWithProgids"; ValueType: string; ValueName: "{#MyAppAssocKey}"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\{#MyAppAssocKey}"; ValueType: string; ValueName: ""; ValueData: "{#MyAppAssocName}"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\{#MyAppAssocKey}\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"
Root: HKA; Subkey: "Software\Classes\{#MyAppAssocKey}\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""

[Icons]
; Accesos directos en el menú de inicio y en el escritorio
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Opción final para ejecutar la aplicación inmediatamente al terminar la instalación
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
// --- CÓDIGO PERSONALIZADO PARA LOGICA DE ACTUALIZACIÓN ---
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
  UninstString: String;
begin
  Result := True; // Por defecto, permite que la instalación continúe
  
  // Busca si existe una ruta de desinstalación registrada para este AppId tanto en registros de 64 bits como de 32 bits
  if RegQueryStringValue(HKLM64, 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{FF5F0907-D36D-4EB2-A373-CC9E632B069D}_is1', 'UninstallString', UninstString) or
     RegQueryStringValue(HKLM32, 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{FF5F0907-D36D-4EB2-A373-CC9E632B069D}_is1', 'UninstallString', UninstString) then
  begin
    // Si la encuentra, muestra un cuadro de diálogo al usuario preguntando si desea desinstalar la versión vieja
    if MsgBox('PixelCatchr ya se encuentra instalado en este equipo.' + #13#10#13#10 +
              '¿Deseas desinstalar la versión actual automáticamente antes de continuar?', mbConfirmation, MB_YESNO) = idYes then
    begin
      // Ejecuta el desinstalador existente de forma silenciosa (/SILENT) y evita que reinicie la PC (/NORESTART)
      if Exec(RemoveQuotes(UninstString), '/SILENT /NORESTART', '', SW_SHOW, ewWaitUntilTerminated, ResultCode) then
      begin
        // Espera 1 segundo para asegurar que Windows libere los archivos eliminados del disco
        Sleep(1000);
        Result := True; // Permite proceder con la nueva instalación
      end
      else
      begin
        // Alerta en caso de que falle la desinstalación por permisos o bloqueo
        MsgBox('No se pudo remover la versión anterior automáticamente. Se procederá con la instalación regular.', mbInformation, MB_OK);
        Result := True;
      end;
    end;
  end;
end;