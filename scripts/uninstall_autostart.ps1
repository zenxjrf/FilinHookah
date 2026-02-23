param(
    [string]$TaskName = "FilinBotAutostart"
)

$ErrorActionPreference = "Stop"
$startupDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup"
$startupCmd = Join-Path $startupDir "$TaskName.cmd"

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($task) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Task '$TaskName' removed."
}

if (Test-Path $startupCmd) {
    Remove-Item $startupCmd -Force
    Write-Host "Startup entry removed: $startupCmd"
}
