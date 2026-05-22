param(
    [string]$ConfigPath = (Join-Path $PSScriptRoot "..\config.json"),
    [string]$FirmwareEntriesPath = "",
    [switch]$DryRun,
    [switch]$Reboot,
    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ($FirmwareEntriesPath -and $Reboot) {
    throw "-FirmwareEntriesPath is for dry-run/testing only and cannot be combined with -Reboot."
}

function Assert-Administrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "Run this script from an elevated PowerShell session."
    }
}

function Read-Config {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Config file not found: $Path. Copy config.example.json to config.json and edit it first."
    }

    return Get-Content -Raw -LiteralPath $Path | ConvertFrom-Json
}

function Test-Property {
    param(
        [object]$Object,
        [string]$Name
    )

    return $null -ne $Object.PSObject.Properties[$Name]
}

function Validate-Config {
    param([object]$Config)

    # Keep this in sync with tools/validate_config.py. Windows switching stays
    # PowerShell-native so it does not require Python on the Windows side.
    foreach ($section in @("windows", "linux", "safety")) {
        if (-not (Test-Property -Object $Config -Name $section)) {
            throw "Config error: missing '$section' section."
        }
    }

    if ([string]::IsNullOrWhiteSpace([string]$Config.windows.targetLabel)) {
        throw "Config error: windows.targetLabel must be a non-empty string."
    }

    if ([string]::IsNullOrWhiteSpace([string]$Config.windows.stateDir)) {
        throw "Config error: windows.stateDir must be a non-empty string."
    }

    if (-not (Test-Property -Object $Config.windows -Name "rebootTimeoutSeconds")) {
        $Config.windows | Add-Member -NotePropertyName "rebootTimeoutSeconds" -NotePropertyValue 5
    }

    if ((Test-Property -Object $Config -Name "state") -and (Test-Property -Object $Config.state -Name "mode")) {
        $stateMode = ([string]$Config.state.mode).ToLowerInvariant()
        if ($stateMode -notin @("local", "shared")) {
            throw "Config error: state.mode must be either 'local' or 'shared'."
        }

        if ($stateMode -eq "shared") {
            if (-not (Test-Property -Object $Config.state -Name "shared")) {
                throw "Config error: state.shared must be set when state.mode is 'shared'."
            }

            if ([string]::IsNullOrWhiteSpace([string]$Config.state.shared.windowsStateDir)) {
                throw "Config error: state.shared.windowsStateDir must be set when state.mode is 'shared'."
            }
        }
    }

    if (-not (Test-Property -Object $Config.safety -Name "requireConfirmation")) {
        $Config.safety | Add-Member -NotePropertyName "requireConfirmation" -NotePropertyValue $true
    }

    if (-not (Test-Property -Object $Config.safety -Name "pendingTransitionTimeoutMinutes")) {
        $Config.safety | Add-Member -NotePropertyName "pendingTransitionTimeoutMinutes" -NotePropertyValue 10
    }

    if (-not (Test-Property -Object $Config.safety -Name "maxBootFailures")) {
        $Config.safety | Add-Member -NotePropertyName "maxBootFailures" -NotePropertyValue 3
    }

    [void][int]$Config.windows.rebootTimeoutSeconds
    [void][int]$Config.safety.pendingTransitionTimeoutMinutes
    [void][int]$Config.safety.maxBootFailures
}

function Get-EffectiveStateDir {
    param([object]$Config)

    if ((Test-Property -Object $Config -Name "state") -and (Test-Property -Object $Config.state -Name "mode")) {
        $stateMode = ([string]$Config.state.mode).ToLowerInvariant()
        if ($stateMode -eq "shared") {
            return [string]$Config.state.shared.windowsStateDir
        }
    }

    return [string]$Config.windows.stateDir
}

function Initialize-StateDir {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

function Enter-TransitionLock {
    param([string]$StateDir)

    $lockPath = Join-Path $StateDir "transition.lock"
    try {
        New-Item -ItemType Directory -Path $lockPath -ErrorAction Stop | Out-Null
    } catch {
        throw "Another OS Switcher transition appears to be running. Lock path: $lockPath"
    }

    return $lockPath
}

function Exit-TransitionLock {
    param([string]$LockPath)

    if ($LockPath -and (Test-Path -LiteralPath $LockPath)) {
        Remove-Item -LiteralPath $LockPath -Force -Recurse
    }
}

function Test-PendingTransition {
    param(
        [string]$StateDir,
        [int]$TimeoutMinutes,
        [int]$MaxBootFailures
    )

    $pendingPath = Join-Path $StateDir "pending-transition.json"
    $stagedPath = Join-Path $StateDir "transition-staged.json"
    $recoveryPath = Join-Path $StateDir "recovery-mode.json"
    $failCountPath = Join-Path $StateDir "boot-fail-count.txt"

    if (Test-Path -LiteralPath $recoveryPath) {
        throw "OS Switcher is in recovery mode. Inspect $recoveryPath, fix boot health, then run mark-boot-success."
    }

    if (-not (Test-Path -LiteralPath $pendingPath)) {
        if (Test-Path -LiteralPath $stagedPath) {
            $staged = Get-Content -Raw -LiteralPath $stagedPath | ConvertFrom-Json
            $stagedAt = [datetime]::Parse(
                [string]$staged.startedAt,
                $null,
                [System.Globalization.DateTimeStyles]::RoundtripKind
            )
            $stagedAgeMinutes = ((Get-Date).ToUniversalTime() - $stagedAt.ToUniversalTime()).TotalMinutes

            if ($stagedAgeMinutes -lt $TimeoutMinutes) {
                throw "A transition is staged but not complete from $($staged.startedAt). Wait for it to finish, or inspect $stagedPath."
            }

            Rename-Item -LiteralPath $stagedPath -NewName ("failed-staged-transition-{0}.json" -f (Get-Date -Format "yyyyMMdd-HHmmss")) -Force
            throw "A stale staged transition was found and archived. Inspect state directory: $StateDir"
        }

        return
    }

    $pending = Get-Content -Raw -LiteralPath $pendingPath | ConvertFrom-Json
    $startedAt = [datetime]::Parse(
        [string]$pending.startedAt,
        $null,
        [System.Globalization.DateTimeStyles]::RoundtripKind
    )
    $ageMinutes = ((Get-Date).ToUniversalTime() - $startedAt.ToUniversalTime()).TotalMinutes

    if ($ageMinutes -lt $TimeoutMinutes) {
        throw "A transition to '$($pending.target)' is already pending from $($pending.startedAt). Run the boot-success script after a successful boot, or remove $pendingPath if this is stale."
    }

    $failCount = 0
    if (Test-Path -LiteralPath $failCountPath) {
        $failCount = [int](Get-Content -Raw -LiteralPath $failCountPath)
    }
    $failCount += 1
    Set-Content -LiteralPath $failCountPath -Value $failCount -Encoding ASCII

    Rename-Item -LiteralPath $pendingPath -NewName ("failed-transition-{0}.json" -f (Get-Date -Format "yyyyMMdd-HHmmss")) -Force

    if ($failCount -ge $MaxBootFailures) {
        $recovery = [ordered]@{
            enteredAt = (Get-Date).ToUniversalTime().ToString("o")
            bootFailCount = $failCount
            threshold = $MaxBootFailures
        }
        $recovery | ConvertTo-Json | Set-Content -LiteralPath $recoveryPath -Encoding UTF8
        throw "Previous transition exceeded $TimeoutMinutes minutes. Recovery mode is now active at $recoveryPath"
    }

    throw "Previous transition exceeded $TimeoutMinutes minutes and was marked failed ($failCount/$MaxBootFailures). Inspect state directory: $StateDir"
}

function Write-StagedTransition {
    param(
        [string]$StateDir,
        [string]$Target,
        [string]$Identifier
    )

    $staged = [ordered]@{
        target = $Target
        identifier = $Identifier
        startedAt = (Get-Date).ToUniversalTime().ToString("o")
        source = "Windows"
        state = "staged"
    }
    $staged | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $StateDir "transition-staged.json") -Encoding UTF8
}

function Clear-StagedTransition {
    param([string]$StateDir)

    $stagedPath = Join-Path $StateDir "transition-staged.json"
    if (Test-Path -LiteralPath $stagedPath) {
        Remove-Item -LiteralPath $stagedPath -Force
    }
}

function Write-PendingTransition {
    param(
        [string]$StateDir,
        [string]$Target,
        [string]$Identifier,
        [string]$StartedAt
    )

    $pending = [ordered]@{
        target = $Target
        identifier = $Identifier
        startedAt = $StartedAt
        commandSucceededAt = (Get-Date).ToUniversalTime().ToString("o")
        source = "Windows"
        state = "pending"
    }
    $pending | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $StateDir "pending-transition.json") -Encoding UTF8
}

function Get-FirmwareEntries {
    param([string]$FirmwareEntriesPath = "")

    if ($FirmwareEntriesPath) {
        if (-not (Test-Path -LiteralPath $FirmwareEntriesPath)) {
            throw "Firmware entries fixture not found: $FirmwareEntriesPath"
        }
        $lines = Get-Content -LiteralPath $FirmwareEntriesPath
    } else {
        $lines = & bcdedit /enum firmware 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw "bcdedit failed: $($lines -join [Environment]::NewLine)"
        }
    }

    $entries = @()
    $current = $null

    foreach ($line in $lines) {
        if ($line -match "^\s*identifier\s+(\{[^}]+\})") {
            if ($null -ne $current) {
                $entries += [pscustomobject]$current
            }
            $current = @{
                Identifier = $Matches[1]
                Description = ""
            }
            continue
        }

        if ($null -ne $current -and $line -match "^\s*description\s+(.+)$") {
            $current.Description = $Matches[1].Trim()
        }
    }

    if ($null -ne $current) {
        $entries += [pscustomobject]$current
    }

    return $entries
}

function Find-EntryByLabel {
    param(
        [object[]]$Entries,
        [string]$Label
    )

    $matches = @($Entries | Where-Object { $_.Description.IndexOf($Label, [System.StringComparison]::OrdinalIgnoreCase) -ge 0 })
    if ($matches.Count -eq 0) {
        $available = ($Entries | ForEach-Object { "- $($_.Description) $($_.Identifier)" }) -join [Environment]::NewLine
        throw "No firmware entry matched '$Label'. Available entries:$([Environment]::NewLine)$available"
    }

    if ($matches.Count -gt 1) {
        $found = ($matches | ForEach-Object { "- $($_.Description) $($_.Identifier)" }) -join [Environment]::NewLine
        throw "Multiple firmware entries matched '$Label'. Make the config label more specific:$([Environment]::NewLine)$found"
    }

    return $matches[0]
}

$config = Read-Config -Path $ConfigPath
Validate-Config -Config $config
$targetLabel = [string]$config.windows.targetLabel
$timeout = [int]$config.windows.rebootTimeoutSeconds
$stateDir = Get-EffectiveStateDir -Config $config
$pendingTimeout = [int]$config.safety.pendingTransitionTimeoutMinutes
$maxBootFailures = [int]$config.safety.maxBootFailures

if ([string]::IsNullOrWhiteSpace($targetLabel)) {
    throw "windows.targetLabel is required in config."
}

if (-not $FirmwareEntriesPath) {
    Assert-Administrator
}
Initialize-StateDir -Path $stateDir
$lockPath = Enter-TransitionLock -StateDir $stateDir
$scriptExitCode = 0

try {
    do {
        Test-PendingTransition -StateDir $stateDir -TimeoutMinutes $pendingTimeout -MaxBootFailures $maxBootFailures

        $entries = Get-FirmwareEntries -FirmwareEntriesPath $FirmwareEntriesPath
        $target = Find-EntryByLabel -Entries $entries -Label $targetLabel
        $targetIdentifier = "$($target.Identifier)"

        Write-Host "Target Linux firmware entry: $($target.Description) $targetIdentifier"

        if ($DryRun -or -not $Reboot) {
            Write-Host "Dry run: would run bcdedit /set {fwbootmgr} bootsequence $targetIdentifier"
            Write-Host "Dry run: would write pending transition state."
            Write-Host "Dry run: would reboot after $timeout seconds."
            break
        }

        if ($config.safety.requireConfirmation -and -not $Force) {
            $answer = Read-Host "Set next boot to '$($target.Description)' and reboot? Type SWITCH to continue"
            if ($answer -ne "SWITCH") {
                Write-Host "Aborted."
                $scriptExitCode = 1
                break
            }
        }

        Write-StagedTransition -StateDir $stateDir -Target "Linux" -Identifier $targetIdentifier

        $transitionStartedAt = (Get-Date).ToUniversalTime().ToString("o")
        $firmwareCommandSucceeded = $false
        try {
            & bcdedit /set "{fwbootmgr}" bootsequence "$targetIdentifier" | Out-Host
            if ($LASTEXITCODE -ne 0) {
                throw "Failed to set firmware boot sequence."
            }
            $firmwareCommandSucceeded = $true
            Write-PendingTransition -StateDir $stateDir -Target "Linux" -Identifier $targetIdentifier -StartedAt $transitionStartedAt
            Clear-StagedTransition -StateDir $stateDir
        } catch {
            if (-not $firmwareCommandSucceeded) {
                Clear-StagedTransition -StateDir $stateDir
            }
            throw
        }

        shutdown /r /t $timeout /c "Switching to Linux workspace"
    } while ($false)
} finally {
    Exit-TransitionLock -LockPath $lockPath
}

exit $scriptExitCode





