param(
    [string]$ConfigPath = (Join-Path $PSScriptRoot "..\config.json")
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Test-Property {
    param(
        [object]$Object,
        [string]$Name
    )

    return $null -ne $Object.PSObject.Properties[$Name]
}

function Get-EffectiveStateDir {
    param([object]$Config)

    if ((Test-Property -Object $Config -Name "state") -and (Test-Property -Object $Config.state -Name "mode")) {
        $stateMode = ([string]$Config.state.mode).ToLowerInvariant()
        if ($stateMode -eq "shared") {
            if (-not (Test-Property -Object $Config.state -Name "shared") -or [string]::IsNullOrWhiteSpace([string]$Config.state.shared.windowsStateDir)) {
                throw "Config error: state.shared.windowsStateDir must be set when state.mode is 'shared'."
            }
            return [string]$Config.state.shared.windowsStateDir
        }
    }

    if (-not (Test-Property -Object $Config -Name "windows") -or [string]::IsNullOrWhiteSpace([string]$Config.windows.stateDir)) {
        throw "Config error: windows.stateDir must be set."
    }
    return [string]$Config.windows.stateDir
}

if (-not (Test-Path -LiteralPath $ConfigPath)) {
    throw "Config file not found: $ConfigPath"
}

$config = Get-Content -Raw -LiteralPath $ConfigPath | ConvertFrom-Json
$stateDir = Get-EffectiveStateDir -Config $config
$recoveryPath = Join-Path $stateDir "recovery-mode.json"

if (-not (Test-Path -LiteralPath $recoveryPath)) {
    Write-Host "No recovery mode active."
    exit 0
}

Write-Host "=== Current EFI Boot Configuration ==="
try {
    & bcdedit /enum firmware
} catch {
    Write-Warning "Failed to run bcdedit: $_"
}
Write-Host "======================================"

$backupFile = Get-ChildItem -Path $stateDir -Filter "efi-backup-*.txt" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($null -ne $backupFile) {
    $newestBackup = $backupFile.FullName
} else {
    $newestBackup = "No backup files found in $stateDir"
}

Write-Host ""
Write-Host "RECOVERY MODE ACTIVE — Automatic rollback not possible (EFI manipulation is unsafe)."
Write-Host "Please manually restore your boot entries using bcdedit."
Write-Host "Your last EFI backup is at: $newestBackup"
exit 1
