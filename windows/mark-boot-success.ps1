param(
    [string]$ConfigPath = (Join-Path $PSScriptRoot "..\config.json"),
    [switch]$ClearRecovery
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

function Get-MaxBootFailures {
    param([object]$Config)

    if ((Test-Property -Object $Config -Name "safety") -and (Test-Property -Object $Config.safety -Name "maxBootFailures")) {
        return [int]$Config.safety.maxBootFailures
    }
    return 3
}

function Get-BootFailCount {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        return 0
    }
    return [int](Get-Content -Raw -LiteralPath $Path)
}

function Set-RecoveryMode {
    param(
        [string]$Path,
        [int]$BootFailCount,
        [int]$Threshold,
        [string]$Reason
    )

    $recovery = [ordered]@{
        enteredAt = (Get-Date).ToUniversalTime().ToString("o")
        bootFailCount = $BootFailCount
        threshold = $Threshold
        reason = $Reason
    }
    $recovery | ConvertTo-Json | Set-Content -LiteralPath $Path -Encoding UTF8
}

if (-not (Test-Path -LiteralPath $ConfigPath)) {
    throw "Config file not found: $ConfigPath"
}

$config = Get-Content -Raw -LiteralPath $ConfigPath | ConvertFrom-Json
$stateDir = Get-EffectiveStateDir -Config $config
$maxBootFailures = Get-MaxBootFailures -Config $config
if (-not (Test-Path -LiteralPath $stateDir)) {
    New-Item -ItemType Directory -Path $stateDir -Force | Out-Null
}

$pendingPath = Join-Path $stateDir "pending-transition.json"
$successPath = Join-Path $stateDir "last-boot-success.json"
$failCountPath = Join-Path $stateDir "boot-fail-count.txt"
$recoveryPath = Join-Path $stateDir "recovery-mode.json"
$mismatchPath = Join-Path $stateDir "last-boot-mismatch.json"

$hasPending = Test-Path -LiteralPath $pendingPath
$hasFailureState = (Test-Path -LiteralPath $failCountPath) -or (Test-Path -LiteralPath $recoveryPath)

if (-not $hasPending -and -not $hasFailureState) {
    exit 0
}

if ((Test-Path -LiteralPath $recoveryPath) -and -not $ClearRecovery) {
    Write-Host "Recovery mode is active at $recoveryPath. Inspect boot health, then rerun with -ClearRecovery if it is safe."
    exit 0
}

if (-not $hasPending -and $hasFailureState -and -not $ClearRecovery) {
    Write-Host "Failure state exists in $stateDir. Inspect it, then rerun with -ClearRecovery if it is safe."
    exit 0
}

if ($hasPending) {
    $pending = Get-Content -Raw -LiteralPath $pendingPath | ConvertFrom-Json
    $pendingTarget = [string]$pending.target

    if (-not [string]::Equals($pendingTarget, "Windows", [System.StringComparison]::OrdinalIgnoreCase)) {
        $failCount = (Get-BootFailCount -Path $failCountPath) + 1
        Set-Content -LiteralPath $failCountPath -Value $failCount -Encoding ASCII

        $failedName = "failed-transition-{0}.json" -f (Get-Date -Format "yyyyMMdd-HHmmss")
        Rename-Item -LiteralPath $pendingPath -NewName $failedName -Force

        $mismatch = [ordered]@{
            os = "Windows"
            markedAt = (Get-Date).ToUniversalTime().ToString("o")
            expectedTarget = $pendingTarget
            bootFailCount = $failCount
        }
        $mismatch | ConvertTo-Json | Set-Content -LiteralPath $mismatchPath -Encoding UTF8

        if ($failCount -ge $maxBootFailures) {
            Set-RecoveryMode -Path $recoveryPath -BootFailCount $failCount -Threshold $maxBootFailures -Reason "Booted Windows while pending target was '$pendingTarget'."
            throw "Boot target mismatch recorded. Recovery mode is now active at $recoveryPath"
        }

        throw "Boot target mismatch recorded ($failCount/$maxBootFailures). Expected '$pendingTarget' but booted Windows."
    }
}

$success = [ordered]@{
    os = "Windows"
    markedAt = (Get-Date).ToUniversalTime().ToString("o")
    clearedPending = $hasPending
}

if ($hasPending) {
    Remove-Item -LiteralPath $pendingPath -Force
}

foreach ($path in @($failCountPath, $recoveryPath)) {
    if (Test-Path -LiteralPath $path) {
        Remove-Item -LiteralPath $path -Force
    }
}

$success | ConvertTo-Json | Set-Content -LiteralPath $successPath -Encoding UTF8
Write-Host "Marked Windows boot success: $successPath"
