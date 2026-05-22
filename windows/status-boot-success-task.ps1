param(
    [string]$TaskName = "OSSwitcherBootSuccess"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($null -eq $task) {
    Write-Host "Scheduled task is not installed: $TaskName"
    exit 1
}

$info = Get-ScheduledTaskInfo -TaskName $TaskName
Write-Host "Scheduled task: $TaskName"
Write-Host "State: $($task.State)"
Write-Host "Last run time: $($info.LastRunTime)"
Write-Host "Last task result: $($info.LastTaskResult)"
Write-Host "Next run time: $($info.NextRunTime)"
