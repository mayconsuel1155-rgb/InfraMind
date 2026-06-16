[Setup]
AppName=InfraMind Server
AppVersion=1.0
DefaultDirName={pf}\InfraMind Server
DefaultGroupName=InfraMind Server
OutputDir=dist
OutputBaseFilename=InfraMind_Server_Setup
Compression=lzma
SolidCompression=yes
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=admin
SetupIconFile=agent\inframind-agent.ico
UninstallDisplayIcon={app}\inframind-server.exe

[Files]
Source: "backend\dist\inframind-server.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "backend\.env.example"; DestDir: "{commonappdata}\InfraMind"; DestName: ".env"; Flags: uninsneveruninstall onlyifdoesntexist

[Dirs]
Name: "{commonappdata}\InfraMind"; Permissions: users-modify

[Icons]
Name: "{group}\Start InfraMind Server"; Filename: "{app}\inframind-server.exe"; Parameters: "runserver"
Name: "{group}\Diagnosticar InfraMind"; Filename: "{app}\inframind-server.exe"; Parameters: "diagnose"
Name: "{commondesktop}\InfraMind Server"; Filename: "{app}\inframind-server.exe"; Parameters: "runserver"

[Run]
; Run diagnostic first to make sure port is free
Filename: "{app}\inframind-server.exe"; Parameters: "diagnose"; Flags: waituntilterminated; StatusMsg: "Testando portas e banco de dados..."
; Run migrations
Filename: "{app}\inframind-server.exe"; Parameters: "migrate"; Flags: waituntilterminated; StatusMsg: "Configurando banco de dados..."
; Create scheduled task to run on boot
Filename: "schtasks.exe"; Parameters: "/create /tn ""InfraMindServer"" /tr ""\"{app}\inframind-server.exe\" runserver"" /sc onstart /ru ""SYSTEM"" /f"; Flags: runhidden; StatusMsg: "Instalando serviço do Windows..."
; Start the server now
Filename: "schtasks.exe"; Parameters: "/run /tn ""InfraMindServer"""; Flags: runhidden; StatusMsg: "Iniciando InfraMind..."
; Open browser
Filename: "http://localhost:8000"; Flags: shellexec runasoriginaluser; StatusMsg: "Abrindo painel..."

[UninstallRun]
Filename: "schtasks.exe"; Parameters: "/delete /tn ""InfraMindServer"" /f"; Flags: runhidden

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
  // Aqui poderiamos adicionar logicas de download silencioso do Postgres
  // mas como o SQLite sera usado pelo default no ProgramData, e um fallback solido.
end;
