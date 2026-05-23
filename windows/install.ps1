Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "========================================"
Write-Host "  OS Switcher Installer — Windows"
Write-Host "========================================"
Write-Host ""

# --- Step 2: Check running as Administrator ---
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    [Console]::Error.WriteLine("ERROR: This installer must be run as Administrator.")
    exit 1
}
Write-Host "OK   Running as Administrator."

# --- Step 3: Check python is available and >= 3.8 ---
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    [Console]::Error.WriteLine("ERROR: python is not available in PATH.")
    exit 1
}

try {
    $versionOutput = & python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")'
} catch {
    [Console]::Error.WriteLine("ERROR: Failed to run python. Make sure it is installed and in PATH.")
    exit 1
}

$parts = $versionOutput.Trim() -split '\.'
if ($parts.Count -lt 2) {
    [Console]::Error.WriteLine("ERROR: Could not parse Python version.")
    exit 1
}

$major = [int]$parts[0]
$minor = [int]$parts[1]

if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 8)) {
    [Console]::Error.WriteLine("ERROR: Python 3.8+ is required. Current version: $($versionOutput.Trim())")
    exit 1
}
Write-Host "OK   Python $($versionOutput.Trim()) detected."

# --- Step 4: Check bcdedit is available ---
$bcdeditCmd = Get-Command bcdedit -ErrorAction SilentlyContinue
if (-not $bcdeditCmd) {
    [Console]::Error.WriteLine("ERROR: bcdedit is not available.")
    exit 1
}
Write-Host "OK   bcdedit detected."

# --- Step 5: Copy project files to C:\Program Files\OSSwitcher\ ---
$ProjectRoot = (Get-Item (Join-Path $PSScriptRoot "..")).FullName
$InstallDir = "C:\Program Files\OSSwitcher"

Write-Host ""
Write-Host "Installing to $InstallDir ..."

function Copy-ProjectFiles {
    param(
        [string]$Src,
        [string]$Dest
    )

    if (-not (Test-Path -LiteralPath $Dest)) {
        New-Item -ItemType Directory -Path $Dest -Force | Out-Null
    }

    # Define exclusion list
    $excludeNames = @("config.json", "__pycache__", ".git", "dist", "tests")

    # Get all items in source directory (files and folders)
    $items = Get-ChildItem -Path $Src -Force

    foreach ($item in $items) {
        if ($excludeNames -contains $item.Name) {
            continue
        }

        $destPath = Join-Path $Dest $item.Name

        if ($item.PSIsContainer) {
            # Recursively copy directory
            Copy-ProjectFiles -Src $item.FullName -Dest $destPath
        } else {
            # Copy file
            Copy-Item -LiteralPath $item.FullName -Destination $destPath -Force
        }
    }
}

try {
    Copy-ProjectFiles -Src $ProjectRoot -Dest $InstallDir
    Write-Host "OK   Project files copied to $InstallDir."
} catch {
    [Console]::Error.WriteLine("ERROR: Failed to copy project files: $_")
    exit 1
}

# --- Step 6: If config.json does NOT exist in install dir, copy config.example.json there as config.json ---
$configPath = Join-Path $InstallDir "config.json"
$exampleConfigPath = Join-Path $InstallDir "config.example.json"
if (-not (Test-Path -LiteralPath $configPath)) {
    if (Test-Path -LiteralPath $exampleConfigPath) {
        Copy-Item -LiteralPath $exampleConfigPath -Destination $configPath -Force
        Write-Host "OK   config.example.json copied to config.json (edit before first use)."
    } else {
        [Console]::Error.WriteLine("ERROR: config.example.json not found in install dir.")
        exit 1
    }
} else {
    Write-Host "OK   Existing config.json preserved."
}

# --- Step 7: Install boot-success scheduled task ---
Write-Host ""
Write-Host "Installing boot-success scheduled task ..."
& powershell.exe -ExecutionPolicy Bypass -File (Join-Path $InstallDir "windows\install-boot-success-task.ps1") 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    [Console]::Error.WriteLine("ERROR: Failed to install boot-success scheduled task. Exit code: $LASTEXITCODE")
    exit 1
}
Write-Host "OK   Boot-success scheduled task installed."

# --- Step 8: Create Start Menu shortcut ---
$shortcutPath = "C:\ProgramData\Microsoft\Windows\Start Menu\Programs\OS Switcher.lnk"
$shortcutDir = Split-Path -Path $shortcutPath -Parent
if (-not (Test-Path -LiteralPath $shortcutDir)) {
    New-Item -ItemType Directory -Path $shortcutDir -Force | Out-Null
}

$pythonPath = (Get-Command python).Source
$pythonDir = Split-Path -Path $pythonPath -Parent
$pythonwPath = Join-Path $pythonDir "pythonw.exe"
if (-not (Test-Path -LiteralPath $pythonwPath)) {
    $pythonwPath = "pythonw"
}

try {
    $wshShell = New-Object -ComObject WScript.Shell
    $shortcut = $wshShell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = $pythonwPath
    $shortcut.Arguments = "`"C:\Program Files\OSSwitcher\gui\os_switcher_gui.py`""
    $shortcut.WorkingDirectory = "C:\Program Files\OSSwitcher"
    $shortcut.Save()
    Write-Host "OK   Start Menu shortcut created: $shortcutPath"
} catch {
    [Console]::Error.WriteLine("ERROR: Failed to create Start Menu shortcut: $_")
    exit 1
}

# --- Step 9: Print success message ---
Write-Host ""
Write-Host "Installation complete."
Write-Host "Next: Edit C:\Program Files\OSSwitcher\config.json with your EFI GUIDs."
Write-Host "Then launch: OS Switcher from Start Menu"
