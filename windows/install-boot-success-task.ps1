param(
    [string]$ConfigPath = (Join-Path $PSScriptRoot "..\config.json"),
    [string]$TaskName = "OSSwitcherBootSuccess"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Assert-Administrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "Run this installer from an elevated PowerShell session."
    }
}

Assert-Administrator

$scriptPath = Join-Path $PSScriptRoot "mark-boot-success.ps1"
if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw "Boot success script not found: $scriptPath"
}

if (-not (Test-Path -LiteralPath $ConfigPath)) {
    throw "Config file not found: $ConfigPath"
}

$resolvedScript = (Resolve-Path -LiteralPath $scriptPath).Path
$resolvedConfig = (Resolve-Path -LiteralPath $ConfigPath).Path
$actionArgs = "-NoProfile -ExecutionPolicy Bypass -File `"$resolvedScript`" -ConfigPath `"$resolvedConfig`""
$userId = [Security.Principal.WindowsIdentity]::GetCurrent().Name

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $actionArgs
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $userId
$principal = New-ScheduledTaskPrincipal -UserId $userId -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Description "Marks OS Switcher boot success after Windows logon." `
    -Force | Out-Null

Write-Host "Installed scheduled task: $TaskName"
