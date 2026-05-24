; Inno Setup Script for OS Switcher
; Ensures professional installation, setup, and clean uninstallation.

#define FileHandle FileOpen("..\VERSION")
#define MyAppVersion FileRead(FileHandle)
#expr FileClose(FileHandle)

[Setup]
AppId={{A85C3970-DE9F-4D2A-949B-5100C888A21C}}
AppName=OS Switcher
AppVersion={#MyAppVersion}
AppPublisher=Antigravity
DefaultDirName={commonpf}\OSSwitcher
DefaultGroupName=OS Switcher
DisableProgramGroupPage=yes
OutputBaseFilename=OSSwitcher-Setup
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64
SetupIconFile=..\gui\os-switcher-logo.ico
UninstallDisplayIcon={app}\gui\os-switcher-logo.ico

[Files]
; Copy all project files except ignored ones
Source: "..\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "config.json, __pycache__, .git, dist, tests, *.zip, *.pyc, *.exe, .gitattributes, .gitignore, pytest.ini, .pytest_cache"

; Copy config.example.json as config.json if config.json doesn't exist
Source: "..\config.example.json"; DestName: "config.json"; DestDir: "{app}"; Flags: onlyifdoesntexist

[Icons]
Name: "{group}\OS Switcher"; Filename: "pythonw.exe"; Parameters: """{app}\gui\os_switcher_gui.py"""; IconFilename: "{app}\gui\os-switcher-logo.ico"
Name: "{group}\Uninstall OS Switcher"; Filename: "{uninstallexe}"; IconFilename: "{uninstallexe}"

[Run]
; Run the Scheduled Task installer silently
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File ""{app}\windows\install-boot-success-task.ps1"""; Flags: runhidden

; Run the interactive setup wizard as an elevated GUI application
Filename: "pythonw.exe"; Parameters: """{app}\tools\setup_wizard.py"""; Verb: "runas"; Description: "Launch Setup Wizard (Recommended)"; Flags: postinstall nowait shellexec

[UninstallRun]
; Silently clean up the Scheduled Task during uninstall
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File ""{app}\windows\uninstall-boot-success-task.ps1"""; Flags: runhidden
