Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "========================================"
Write-Host "  OS Switcher Uninstaller — Windows"
Write-Host "========================================"
Write-Host ""

# --- Step 1: Check running as Administrator ---
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    [Console]::Error.WriteLine("ERROR: This uninstaller must be run as Administrator.")
    exit 1
}
Write-Host "OK   Running as Administrator."

$InstallDir = "C:\Program Files\OSSwitcher"

# --- Step 2: Remove boot-success scheduled task ---
Write-Host ""
Write-Host "Removing boot-success scheduled task ..."
$taskScript = Join-Path $InstallDir "windows\uninstall-boot-success-task.ps1"
if (Test-Path -LiteralPath $taskScript) {
    & powershell.exe -ExecutionPolicy Bypass -File $taskScript 2>&1 | Out-Null
    Write-Host "OK   Boot-success scheduled task removed."
} else {
    Write-Host "SKIP Task uninstall script not found (already removed?)."
}

# --- Step 3: Remove Start Menu shortcut ---
$shortcutPath = "C:\ProgramData\Microsoft\Windows\Start Menu\Programs\OS Switcher.lnk"
if (Test-Path -LiteralPath $shortcutPath) {
    Remove-Item -LiteralPath $shortcutPath -Force
    Write-Host "OK   Start Menu shortcut removed."
} else {
    Write-Host "SKIP Start Menu shortcut not found."
}

# --- Step 4: Remove install directory ---
if (Test-Path -LiteralPath $InstallDir) {
    Remove-Item -LiteralPath $InstallDir -Recurse -Force
    Write-Host "OK   Removed install directory: $InstallDir"
} else {
    Write-Host "SKIP Install directory not found: $InstallDir"
}

# --- Done ---
Write-Host ""
Write-Host "========================================"
Write-Host "  Uninstall complete."
Write-Host "========================================"
Write-Host ""
Write-Host "NOTE: Your state directory was NOT removed."
Write-Host "      It may contain transition state and EFI backups."
Write-Host "      Default location: C:\ProgramData\OSSwitcher"
Write-Host "      To confirm, check the stateDir value in your config."
