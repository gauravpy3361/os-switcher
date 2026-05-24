; Inno Setup Script for OS Switcher
; Ensures professional installation, setup, and clean uninstallation.

[Setup]
AppId={{A85C3970-DE9F-4D2A-949B-5100C888A21C}}
AppName=OS Switcher
AppVersion=1.0.0
AppPublisher=Antigravity
DefaultDirName={commonpf}\OSSwitcher
DefaultGroupName=OS Switcher
DisableProgramGroupPage=yes
OutputBaseFilename=OSSwitcher-Setup
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64
UninstallDisplayIcon={app}\gui\os_switcher_gui.py

[Files]
; Copy all project files except ignored ones
Source: "..\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "config.json, __pycache__, .git, dist, tests, *.zip, *.pyc, *.exe, .gitattributes, .gitignore, pytest.ini, .pytest_cache"

; Copy config.example.json as config.json if config.json doesn't exist
Source: "..\config.example.json"; DestName: "config.json"; DestDir: "{app}"; Flags: onlyifdoesntexist

[Icons]
Name: "{group}\OS Switcher"; Filename: "pythonw.exe"; Parameters: """{app}\gui\os_switcher_gui.py"""
Name: "{group}\Uninstall OS Switcher"; Filename: "{uninstallexe}"

[Run]
; Run the Scheduled Task installer silently
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File ""{app}\windows\install-boot-success-task.ps1"""; Flags: runhidden

; Run the interactive setup wizard in a new terminal window
Filename: "cmd.exe"; Parameters: "/k python ""{app}\tools\setup_wizard.py"" & pause"; Description: "Launch Setup Wizard"; Flags: postinstall nowait shellexec

[UninstallRun]
; Silently clean up the Scheduled Task during uninstall
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File ""{app}\windows\uninstall-boot-success-task.ps1"""; Flags: runhidden
