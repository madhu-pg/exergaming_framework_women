; Inno Setup Script for Exercise Game
; Creates Windows installer for Python exercise game with camera pose detection

#define MyAppName "Exercise Game"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Your Organization"
#define MyAppExeName "ExerciseApp.exe"

[Setup]
; NOTE: Generate a unique GUID using Tools > Generate GUID in Inno Setup
; Replace the GUID below with your generated GUID
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\ExerciseApp
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
; LicenseFile=..\LICENSE.txt  ; Uncomment and create LICENSE.txt if needed
OutputDir=..\installer_output
OutputBaseFilename=ExerciseApp_Setup_v{#MyAppVersion}
SetupIconFile=..\app_icon.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
MinVersion=10.0
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Application files from PyInstaller dist folder
Source: "..\dist\ExerciseApp\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Dirs]
; Create writable data directory in AppData for CSV results and logs
Name: "{localappdata}\ExerciseApp"
Name: "{localappdata}\ExerciseApp\game_logs"

[Icons]
; Start Menu shortcuts
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"

; Desktop shortcut
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Option to launch application after installation
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Clean up AppData on uninstall
Type: filesandordirs; Name: "{localappdata}\ExerciseApp"

[Code]
{ Custom Pascal code for installation logic }

function InitializeSetup(): Boolean;
begin
  { Windows 10 check is handled by MinVersion=10.0 in [Setup] section }
  Result := True;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  AppDataDir: String;
begin
  { Post-install: ensure writable data directories exist }
  if CurStep = ssPostInstall then
  begin
    AppDataDir := ExpandConstant('{localappdata}\ExerciseApp');
    ForceDirectories(AppDataDir);
    ForceDirectories(AppDataDir + '\game_logs');
  end;
end;

function InitializeUninstall(): Boolean;
var
  Response: Integer;
begin
  Result := True;
  { Ask user if they want to keep their game data }
  Response := MsgBox('Do you want to delete your exercise results and game logs?', mbConfirmation, MB_YESNO or MB_DEFBUTTON2);
  if Response = IDNO then
  begin
    { User wants to keep data - this will be handled by conditional UninstallDelete }
    Result := True;
  end;
end;

{ Additional helper to check for camera availability - optional }
function CheckCameraAvailable(): Boolean;
begin
  { Note: This is a placeholder - actual camera detection would require }
  { external DLL or more complex WMI queries }
  Result := True;
  { Display a reminder about camera requirements }
  MsgBox('Important: This application requires a webcam for exercise tracking.' + #13#10 +
         'Please ensure your camera is connected and accessible.', mbInformation, MB_OK);
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  { Show camera reminder on the ready-to-install page }
  if CurPageID = wpReady then
  begin
    CheckCameraAvailable();
  end;
end;
