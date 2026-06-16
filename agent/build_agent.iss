[Setup]
AppName=InfraMind Agent
AppVersion=1.0
DefaultDirName={pf}\InfraMind Agent
DefaultGroupName=InfraMind Agent
OutputDir=dist
OutputBaseFilename=InfraMind_Agent_Setup
Compression=lzma
SolidCompression=yes
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=admin
SetupIconFile=inframind-agent.ico
UninstallDisplayIcon={app}\inframind-agent.exe

[Files]
Source: "dist\inframind-agent.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "config.json"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Start InfraMind Agent"; Filename: "{app}\inframind-agent.exe"

[Run]
; Create scheduled task to run on boot
Filename: "schtasks.exe"; Parameters: "/create /tn ""InfraMindAgent"" /tr ""\"{app}\inframind-agent.exe\""" /sc onstart /ru ""SYSTEM"" /f"; Flags: runhidden; StatusMsg: "Configurando agente no Windows..."
; Start the agent now
Filename: "schtasks.exe"; Parameters: "/run /tn ""InfraMindAgent"""; Flags: runhidden; StatusMsg: "Iniciando monitoramento..."

[UninstallRun]
Filename: "schtasks.exe"; Parameters: "/delete /tn ""InfraMindAgent"" /f"; Flags: runhidden
Filename: "taskkill.exe"; Parameters: "/f /im inframind-agent.exe"; Flags: runhidden
