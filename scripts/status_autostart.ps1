param(
    [string]$TaskName = "FilinBotAutostart"
)

$ErrorActionPreference = "Stop"
$startupDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup"
$startupCmd = Join-Path $startupDir "$TaskName.cmd"

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($task) {
    $info = Get-ScheduledTaskInfo -TaskName $TaskName
    Write-Host "Mode: TaskScheduler"
    Write-Host "TaskName: $TaskName"
    Write-Host "State: $($info.State)"
    Write-Host "LastRunTime: $($info.LastRunTime)"
    Write-Host "LastTaskResult: $($info.LastTaskResult)"
    Write-Host "NextRunTime: $($info.NextRunTime)"
    exit 0
}

if (Test-Path $startupCmd) {
    Write-Host "Mode: StartupFolder"
    Write-Host "Path: $startupCmd"
    exit 0
}

Write-Host "Autostart is not installed."
exit 1
